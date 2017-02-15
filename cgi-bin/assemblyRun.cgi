#!/usr/bin/perl -w
use strict;
use CGI qw(:standard);
use CGI::Carp qw ( fatalsToBrowser ); 
use JSON; #JSON::XS is recommended to be installed for handling JSON string of big size 
use DBI;
use lib "lib/";
use lib "lib/pangu";
use pangu;
use user;
use userConfig;
use userCookie;

my $userCookie = new userCookie;
my $userId = (cookie('cid')) ? $userCookie->checkCookie(cookie('cid')) : 0;
exit if (!$userId);

my $user = new user;
my $userDetail = $user->getAllFieldsWithUserId($userId);
my $userName = $userDetail->{"userName"};

my $commoncfg = readConfig("main.conf");
my $dbh=DBI->connect("DBI:mysql:$commoncfg->{DATABASE}:$commoncfg->{DBHOST}",$commoncfg->{USERNAME},$commoncfg->{PASSWORD});
my $userConfig = new userConfig;

my $alignEngineList;
$alignEngineList->{'blastn'} = "blast+/bin/blastn";
$alignEngineList->{'BLAT'} = "blat";
my $windowmasker = 'blast+/bin/windowmasker';
my $makeblastdb = 'blast+/bin/makeblastdb';

my $assemblyId = param ('assemblyId') || '';
my $replace = param ('replace') || '0';
my $fpcOrAgpId = param ('fpcOrAgpId') || '0';
my $refGenomeId = param ('refGenomeId') || '0';
my $assignChr = param ('assignChr') || '0';
my $orientContigs = param ('orientContigs') || '0';
my $seqToSeq = param ('seqToSeq') || '0';
my $identitySeqToSeq = param ('identitySeqToSeq') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOSEQIDENTITY");
my $minOverlapSeqToSeq = param ('minOverlapSeqToSeq') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOSEQMINOVERLAP");
my $redoAllSeqToSeq = param ('redoAllSeqToSeq') || '0';
my $checkGood = param ('checkGood') || '0';
my $seqToGenome = param ('seqToGenome') || '0';
my $identitySeqToGenome = param ('identitySeqToGenome') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOGNMIDENTITY");
my $minOverlapSeqToGenome = param ('minOverlapSeqToGenome') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOGNMMINOVERLAP");
my $alignEngine = param ('alignEngine') || 'blastn';
my $task = param ('megablast') || 'blastn';
my $seqToSeqTask = param ('seqToSeqMegablast') || 'blastn';
my $softMasking = param ('softMasking') || '0';
my $redoAllSeqToGenome = param ('redoAllSeqToGenome') || '0';
my $markRepeatRegion = param ('markRepeatRegion') || '0';
my $endToEnd = param ('endToEnd') || '0';
my $identityEndToEnd = param ('identityEndToEnd') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"ENDTOENDIDENTITY");
my $minOverlapEndToEnd = param ('minOverlapEndToEnd') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"ENDTOENDMINOVERLAP");
my $redundancyFilterSeq = param ('redundancyFilterSeq') || '0';
my $redundancySeq = 0;
my $redundancyFilterOverlap = param ('redundancyFilterOverlap') || '0';
my $orientSeqs = param ('orientSeqs') || '0';
my $renumber = param ('renumber') || '0';
my $gapLength = 100;
print header;

if($assemblyId)
{
	my $pid = fork();
	if ($pid) {
		print <<END;
<script>
	parent.closeDialog();
</script>	
END
	}
	elsif($pid == 0){
		#connect to the mysql server
		my $dbh=DBI->connect("DBI:mysql:$commoncfg->{DATABASE}:$commoncfg->{DBHOST}",$commoncfg->{USERNAME},$commoncfg->{PASSWORD});
		my $assembly=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$assembly->execute($assemblyId);
		my @assembly = $assembly->fetchrow_array();
		if ($assembly[7] > 1 || $assembly[7] < 0) # exit if not for assembly
		{
			print <<END;
<script>
	parent.errorPop("This assembly is frozen or running. Nothing changed.");
</script>	
END
			exit;
		}
		else
		{
		print <<END;
<script>
	parent.refresh("menu");
	parent.errorPop("It's running! This processing might take a while.");
</script>	
END
		}
		close (STDOUT);

		my $target=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$target->execute($assembly[4]);
		my @target = $target->fetchrow_array();

		my $inAssemblySequenceId;
		my $assemblySequenceLength;
		my $assemblySequenceName;
		my $assemblySequenceId;
		my $updateAssemblyToRunning=$dbh->do("UPDATE matrix SET barcode = '-1' WHERE id = $assemblyId");
		if($replace) #delete existing information
		{
			my $assemblySeqs = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblySeq' AND o = ?");
			$assemblySeqs->execute($assemblyId);
			while(my @assemblySeqs = $assemblySeqs->fetchrow_array())
			{
				$inAssemblySequenceId->{$assemblySeqs[5]} = 1;
			}
			my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE container LIKE 'assemblyCtg' AND o = $assemblyId");
			my $deleteAssemblySeq=$dbh->do("DELETE FROM matrix WHERE container LIKE 'assemblySeq' AND o = $assemblyId");

			#initialize assembly
			my $assemblyCtgNumber = 0;
			if($target[1] eq 'library')
			{
				my $getClones = $dbh->prepare("SELECT * FROM clones WHERE libraryId = ? AND sequenced > 0");
				$getClones->execute($assembly[4]);
				while(my @getClones= $getClones->fetchrow_array())
				{
					my @assemblySeqList;
					my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o < 50 AND name LIKE ? ORDER BY y DESC");
					$getSequences->execute($getClones[1]);
					while(my @getSequences = $getSequences->fetchrow_array())
					{
						$assemblySequenceLength->{$getSequences[0]} = $getSequences[5];
						$assemblySequenceName->{$getSequences[0]} = $getSequences[2];
						my $insertAssemblySeq=$dbh->prepare("INSERT INTO matrix VALUES ('', 'assemblySeq', ?, ?, 0, ?, ?, 1, ?, ?, NOW())");
						$insertAssemblySeq->execute($getSequences[2],$assemblyId,$getSequences[0],$getSequences[5],"1,$getSequences[5]",$userName);
						my $assemblySeqId = $dbh->{mysql_insertid};
						$assemblySequenceId->{$assemblySeqId} = $getSequences[0];
						if (@assemblySeqList)
						{
							push @assemblySeqList,"-($assemblySeqId)";
						}
						else
						{
							push @assemblySeqList,"($assemblySeqId)";
						}
					}
					my $assemblySeqList = join ",", @assemblySeqList;
					$assemblyCtgNumber++;
					my $insertAssemblyCtg=$dbh->prepare("INSERT INTO matrix VALUES ('', 'assemblyCtg', ?, ?, 0, 0, 0, 0, ?, ?, NOW())");
					$insertAssemblyCtg->execute($assemblyCtgNumber,$assemblyId,$assemblySeqList,$userName);
				}
			}
			if($target[1] eq 'genome')
			{
				my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = ? ORDER BY id");
				$getSequences->execute($assembly[4]);
				while(my @getSequences = $getSequences->fetchrow_array())
				{
					$assemblySequenceLength->{$getSequences[0]} = $getSequences[5];
					$assemblySequenceName->{$getSequences[0]} = $getSequences[2];
					my $insertAssemblySeq=$dbh->prepare("INSERT INTO matrix VALUES ('', 'assemblySeq', ?, ?, 0, ?, ?, 1, ?, ?, NOW())");
					$insertAssemblySeq->execute($getSequences[2],$assemblyId,$getSequences[0],$getSequences[5],"1,$getSequences[5]",$userName);
					my $assemblySeqId = $dbh->{mysql_insertid};
					$assemblySequenceId->{$assemblySeqId} = $getSequences[0];
					$assemblyCtgNumber++;
					my $insertAssemblyCtg=$dbh->prepare("INSERT INTO matrix VALUES ('', 'assemblyCtg', ?, ?, 0, 0, 0, 0, ?, ?, NOW())");
					$insertAssemblyCtg->execute($assemblyCtgNumber,$assemblyId,"($assemblySeqId)",$userName);
				}
			}
		}
		else
		{
			my $assemblyCtgNumber = 0;
			my $cloneInAssemblyCtg;
			my $assemblySeqs = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblySeq' AND o = ?");
			$assemblySeqs->execute($assemblyId);
			while(my @assemblySeqs = $assemblySeqs->fetchrow_array())
			{
				$inAssemblySequenceId->{$assemblySeqs[5]} = 1;
				my $assemblyCtgOfSeq = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND MATCH (note) AGAINST (?)");
				$assemblyCtgOfSeq->execute("($assemblySeqs[0])");
				my @assemblyCtgOfSeq = $assemblyCtgOfSeq->fetchrow_array();
				$assemblySequenceLength->{$assemblySeqs[5]} = $assemblySeqs[6];
				$assemblySequenceName->{$assemblySeqs[5]} = $assemblySeqs[2];
				$assemblySequenceId->{$assemblySeqs[0]} = $assemblySeqs[5];
				$cloneInAssemblyCtg->{$assemblySeqs[2]} = $assemblyCtgOfSeq[0];
				$assemblyCtgNumber = $assemblyCtgOfSeq[2] if($assemblyCtgOfSeq[2] > $assemblyCtgNumber);
			}
			if($target[1] eq 'library')
			{
				my $getClones = $dbh->prepare("SELECT * FROM clones WHERE libraryId = ? AND sequenced > 0");
				$getClones->execute($assembly[4]);
				while(my @getClones= $getClones->fetchrow_array())
				{
					my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o < 50 AND name LIKE ? ORDER BY y DESC");
					$getSequences->execute($getClones[1]);
					while(my @getSequences = $getSequences->fetchrow_array())
					{
						next if (exists $assemblySequenceLength->{$getSequences[0]}); #skip if seq has been assembled
						$assemblySequenceLength->{$getSequences[0]} = $getSequences[5];
						$assemblySequenceName->{$getSequences[0]} = $getSequences[2];
						my $insertAssemblySeq=$dbh->prepare("INSERT INTO matrix VALUES ('', 'assemblySeq', ?, ?, 0, ?, ?, 1, ?, ?, NOW())");
						$insertAssemblySeq->execute($getSequences[2],$assemblyId,$getSequences[0],$getSequences[5],"1,$getSequences[5]",$userName);
						my $assemblySeqId = $dbh->{mysql_insertid};
						$assemblySequenceId->{$assemblySeqId} = $getSequences[0];
						if(exists $cloneInAssemblyCtg->{$getSequences[2]})
						{
							my $assemblyCtg=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
							$assemblyCtg->execute($cloneInAssemblyCtg->{$getSequences[2]});
							my @assemblyCtg = $assemblyCtg->fetchrow_array();
							my @newAssemblyCtgSeqList;
							my $flag = 1;
							foreach (split ",", $assemblyCtg[8])
							{
								next unless ($_);
								push @newAssemblyCtgSeqList, $_;
								if($flag)
								{
									$_ =~ s/[^a-zA-Z0-9]//g;
									my $assemblySeqList=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
									$assemblySeqList->execute($_);
									my @assemblySeqList = $assemblySeqList->fetchrow_array();
									if($assemblySeqList[2] eq $getSequences[2])
									{
										push @newAssemblyCtgSeqList, "-($assemblySeqId)";
										$flag = 0;
									}
								}
							}								
							$assemblyCtg[8] = join ",",@newAssemblyCtgSeqList;
							my $updateAssemblyCtg=$dbh->prepare("UPDATE matrix SET note = ? WHERE id = ?");
							$updateAssemblyCtg->execute($assemblyCtg[8],$assemblyCtg[0]);
						}
						else
						{
							$assemblyCtgNumber++;
							my $insertAssemblyCtg=$dbh->prepare("INSERT INTO matrix VALUES ('', 'assemblyCtg', ?, ?, 0, 0, 0, 0, ?, ?, NOW())");
							$insertAssemblyCtg->execute($assemblyCtgNumber,$assemblyId,"($assemblySeqId)",$userName);
						}
					}
				}
			}
			if($target[1] eq 'genome')
			{
				my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = ? ORDER BY id");
				$getSequences->execute($assembly[4]);
				while(my @getSequences = $getSequences->fetchrow_array())
				{
					next if (exists $assemblySequenceLength->{$getSequences[0]}); #skip if seq has been assembled
					$assemblyCtgNumber++;
					$assemblySequenceLength->{$getSequences[0]} = $getSequences[5];
					$assemblySequenceName->{$getSequences[0]} = $getSequences[2];
					my $insertAssemblySeq=$dbh->prepare("INSERT INTO matrix VALUES ('', 'assemblySeq', ?, ?, 0, ?, ?, 1, ?, ?, NOW())");
					$insertAssemblySeq->execute($getSequences[2],$assemblyId,$getSequences[0],$getSequences[5],"1,$getSequences[5]",$userName);
					my $assemblySeqId = $dbh->{mysql_insertid};
					$assemblySequenceId->{$assemblySeqId} = $getSequences[0];
					my $insertAssemblyCtg=$dbh->prepare("INSERT INTO matrix VALUES ('', 'assemblyCtg', ?, ?, 0, 0, 0, 0, ?, ?, NOW())");
					$insertAssemblyCtg->execute($assemblyCtgNumber,$assemblyId,"($assemblySeqId)",$userName);
				}
			}
		}

		if($seqToSeq)
		{
			my $updateAssemblyToRunningSeqToSeq=$dbh->do("UPDATE matrix SET barcode = '-2' WHERE id = $assemblyId");

			open (SEQALL,">/tmp/$assembly[4].$$.seq") or die "can't open file: /tmp/$assembly[4].$$.seq";
			open (SEQNEW,">/tmp/$assembly[4].$$.new.seq") or die "can't open file: /tmp/$assembly[4].$$.new.seq";
			if($target[1] eq 'library')
			{
				my $getClones = $dbh->prepare("SELECT * FROM clones WHERE sequenced > 0 AND libraryId = ?");
				$getClones->execute($assembly[4]);
				while(my @getClones = $getClones->fetchrow_array())
				{
					my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o < 50 AND name LIKE ?");
					$getSequences->execute($getClones[1]);
					while(my @getSequences = $getSequences->fetchrow_array())
					{
						$assemblySequenceLength->{$getSequences[0]} = $getSequences[5];
						my $sequenceDetails = decode_json $getSequences[8];
						$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
						$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
						$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
						$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
						print SEQALL ">$getSequences[0]\n$sequenceDetails->{'sequence'}\n";
						print SEQNEW ">$getSequences[0]\n$sequenceDetails->{'sequence'}\n" if (!exists $inAssemblySequenceId->{$getSequences[0]});
					}
				}
			}
			if($target[1] eq 'genome')
			{
				my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = ?");
				$getSequences->execute($assembly[4]);
				while(my @getSequences = $getSequences->fetchrow_array())
				{
					$assemblySequenceLength->{$getSequences[0]} = $getSequences[5];
					my $sequenceDetails = decode_json $getSequences[8];
					$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
					$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
					$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
					$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
					print SEQALL ">$getSequences[0]\n$sequenceDetails->{'sequence'}\n";
					print SEQNEW ">$getSequences[0]\n$sequenceDetails->{'sequence'}\n" if (!exists $inAssemblySequenceId->{$getSequences[0]});
				}
			}
			close(SEQALL);
			close(SEQNEW);
			system( "$makeblastdb -in /tmp/$assembly[4].$$.seq -dbtype nucl" );
			my $goodSequenceId;
			if($redoAllSeqToSeq)
			{
				open (CMD,"$alignEngineList->{'blastn'} -query /tmp/$assembly[4].$$.seq -task $seqToSeqTask -db /tmp/$assembly[4].$$.seq -dust no -evalue 1e-200 -perc_identity $identitySeqToSeq -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
			}
			else
			{
				open (CMD,"$alignEngineList->{'blastn'} -query /tmp/$assembly[4].$$.new.seq -task $seqToSeqTask -db /tmp/$assembly[4].$$.seq -dust no -evalue 1e-200 -perc_identity $identitySeqToSeq -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
			}
			while(<CMD>)
			{
				/^#/ and next;
				my @hit = split("\t",$_);
				next if($hit[0] eq $hit[1]);
				next if($hit[3] < $minOverlapSeqToSeq);
				my $rerunBlastTwo = 0;
				if($hit[0] < $hit[1])
				{
					unless(exists $goodSequenceId->{$hit[0]}->{$hit[1]})
					{
						$goodSequenceId->{$hit[0]}->{$hit[1]} = 1;
						$rerunBlastTwo = 1;
					}
				}
				else
				{
					unless(exists $goodSequenceId->{$hit[1]}->{$hit[0]})
					{
						$goodSequenceId->{$hit[1]}->{$hit[0]} = 1;
						$rerunBlastTwo = 1;
					}
				}
				if($rerunBlastTwo)
				{
					my $deleteAlignmentA = $dbh->do("DELETE FROM alignment WHERE query = $hit[0] AND subject = $hit[1]");
					my $deleteAlignmentB = $dbh->do("DELETE FROM alignment WHERE query = $hit[1] AND subject = $hit[0]");

					unless(-e "/tmp/$hit[0].$$.seq")
					{
						my $getSequenceA = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$getSequenceA->execute($hit[0]);
						my @getSequenceA =  $getSequenceA->fetchrow_array();
						open (SEQA,">/tmp/$getSequenceA[0].$$.seq") or die "can't open file: /tmp/$getSequenceA[0].$$.seq";
						my $sequenceDetailsA = decode_json $getSequenceA[8];
						$sequenceDetailsA->{'id'} = '' unless (exists $sequenceDetailsA->{'id'});
						$sequenceDetailsA->{'description'} = '' unless (exists $sequenceDetailsA->{'description'});
						$sequenceDetailsA->{'sequence'} = '' unless (exists $sequenceDetailsA->{'sequence'});
						$sequenceDetailsA->{'gapList'} = '' unless (exists $sequenceDetailsA->{'gapList'});
						print SEQA ">$getSequenceA[0]\n$sequenceDetailsA->{'sequence'}\n";
						close(SEQA);
					}
					unless(-e "/tmp/$hit[1].$$.seq")
					{
						my $getSequenceB = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$getSequenceB->execute($hit[1]);
						my @getSequenceB =  $getSequenceB->fetchrow_array();
						open (SEQB,">/tmp/$getSequenceB[0].$$.seq") or die "can't open file: /tmp/$getSequenceB[0].$$.seq";
						my $sequenceDetailsB = decode_json $getSequenceB[8];
						$sequenceDetailsB->{'id'} = '' unless (exists $sequenceDetailsB->{'id'});
						$sequenceDetailsB->{'description'} = '' unless (exists $sequenceDetailsB->{'description'});
						$sequenceDetailsB->{'sequence'} = '' unless (exists $sequenceDetailsB->{'sequence'});
						$sequenceDetailsB->{'gapList'} = '' unless (exists $sequenceDetailsB->{'gapList'});
						print SEQB ">$getSequenceB[0]\n$sequenceDetailsB->{'sequence'}\n";
						close(SEQB);
					}

					my @alignments;
					my $goodOverlap = ($checkGood) ? 0 : 1;
					open (CMDA,"$alignEngineList->{'blastn'} -query /tmp/$getSequenceA[0].$$.seq -subject /tmp/$getSequenceB[0].$$.seq -dust no -evalue 1e-200 -perc_identity $identitySeqToSeq -outfmt 6 |") or die "can't open CMD: $!";
					while(<CMDA>)
					{
						/^#/ and next;
						my @hit = split("\t",$_);
						if($hit[3] >= $minOverlapSeqToSeq)
						{
							push @alignments, $_;
							if($hit[6] == 1 || $hit[7] == $getSequenceA[5])
							{
								$goodOverlap = 1;
							}
						}									
					}
					close(CMDA);
					open (CMDB,"$alignEngineList->{'blastn'} -query /tmp/$getSequenceB[0].$$.seq -subject /tmp/$getSequenceA[0].$$.seq -dust no -evalue 1e-200 -perc_identity $identitySeqToSeq -outfmt 6 |") or die "can't open CMD: $!";
					while(<CMDB>)
					{
						/^#/ and next;
						my @hit = split("\t",$_);
						if($hit[3] >= $minOverlapSeqToSeq)
						{
							push @alignments, $_;
							if($hit[6] == 1 || $hit[7] == $getSequenceB[5])
							{
								$goodOverlap = 1;
							}
						}									
					}
					close(CMDB);						
					if($goodOverlap)
					{
						foreach (@alignments)
						{
							my @hit = split("\t",$_);
							#write to alignment
							my $insertAlignment=$dbh->prepare("INSERT INTO alignment VALUES ('', 'SEQtoSEQ\_1e-200\_$identitySeqToSeq\_$minOverlapSeqToSeq', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)");
							$insertAlignment->execute(@hit);
						}
					}
				}
			}
			close(CMD);
			unlink("/tmp/$assembly[4].$$.seq");
			unlink("/tmp/$assembly[4].$$.new.seq");
			unlink("/tmp/$assembly[4].$$.seq.nhr");
			unlink("/tmp/$assembly[4].$$.seq.nin");
			unlink("/tmp/$assembly[4].$$.seq.nsq");
			`rm $commoncfg->{TMPDIR}/*.aln.html`; #delete cached files
			foreach my $queryId (keys %$goodSequenceId)
			{
				unlink("/tmp/$queryId.$$.seq");
				foreach my $subjectId (keys %{$goodSequenceId->{$queryId}})
				{
					unlink("/tmp/$subjectId.$$.seq");
				}
			}

			my $updateAssemblyToRunningStatus=$dbh->do("UPDATE matrix SET barcode = '-1' WHERE id = $assemblyId");
		}

		if($fpcOrAgpId) #merge contigs based on fpc
		{
			my $updateAssemblyToRunningFpc=$dbh->do("UPDATE matrix SET barcode = '-3' WHERE id = $assemblyId");
			my $updateAssemblyFpcId=$dbh->do("UPDATE matrix SET z = $fpcOrAgpId WHERE id = $assemblyId");
			my $assemblySeqCtg;
			my $assemblySeqCtgId;
			my $assemblyCtgList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ?");
			$assemblyCtgList->execute($assemblyId);
			while (my @assemblyCtgList = $assemblyCtgList->fetchrow_array())
			{
				foreach (split ",", $assemblyCtgList[8])
				{
					next unless ($_);
					$_ =~ s/[^a-zA-Z0-9]//g;
					my $assemblySeq = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$assemblySeq->execute($_);
					my @assemblySeq = $assemblySeq->fetchrow_array();
					$assemblySeqCtg->{$assemblySeq[5]} = $assemblyCtgList[2];
					$assemblySeqCtgId->{$assemblySeq[5]} = $assemblyCtgList[0];
				}
			}

			my $fpcOrAgp=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
			$fpcOrAgp->execute($fpcOrAgpId);
			my @fpcOrAgp = $fpcOrAgp->fetchrow_array();
			
			if($fpcOrAgp[1] eq 'fpc')
			{
				my $fpcCtg;
				my $fpcCtgList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'fpcCtg' AND o = ?");
				$fpcCtgList->execute($fpcOrAgpId);
				while (my @fpcCtgList = $fpcCtgList->fetchrow_array())
				{
					$fpcCtg->{$fpcCtgList[2]} = $fpcCtgList[8];
				}
				my @fpcCtg = map  { $_->[0] }
						 sort { $a->[1] <=> $b->[1] }
						 map  { [$_, $_=~/(\d+)/] }
						 keys %$fpcCtg;
				for my $eachFpcCtg (@fpcCtg)
				{
					next if ($eachFpcCtg eq 'Ctg0');
					my $fpcSeq; #fpcSeq
					my $fpcCloneLeftEnd;
					my $fpcCloneRightEnd;
					my $fpcCloneMaxEnd = 0;
					my $fpcCloneList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'fpcClone' AND x > 0 AND o = ? AND MATCH (note) AGAINST (?)");
																							# fpcClone Sequenced(x > 0), no matter MTP marked(y > 0) or not.
					$fpcCloneList->execute($fpcOrAgpId,$eachFpcCtg);
					while (my @fpcCloneList = $fpcCloneList->fetchrow_array())
					{
						my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o < 50 AND name LIKE ?");
						$getSequences->execute($fpcCloneList[2]);
						while(my @getSequences = $getSequences->fetchrow_array())
						{
							$fpcSeq->{$getSequences[0]} = $fpcCloneList[8];
							$fpcCloneList[8] =~ /Ends Left (\d*)/;
							$fpcCloneLeftEnd->{$getSequences[0]} = $1;
							$fpcCloneList[8] =~ /Ends Right (\d*)/;
							$fpcCloneRightEnd->{$getSequences[0]} = $1;
							$fpcCloneMaxEnd = $1 if ($1 > $fpcCloneMaxEnd);
						}
					}
					my @fpcSeq = sort { $fpcCloneLeftEnd->{$a} <=> $fpcCloneLeftEnd->{$b} } keys %$fpcCloneLeftEnd;
					if(@fpcSeq > 1)
					{
						my $preSeq = shift @fpcSeq;
						for my $eachFpcSeq (@fpcSeq)
						{
							#1 read preSeq contig;
							#2 read currentSeq contig;
							#3 compare contigs, if the same, do nothing; if not, go to 4
							if($assemblySeqCtg->{$preSeq} ne $assemblySeqCtg->{$eachFpcSeq})
							{
								#4 check overlap, if not overlapped, do nothing; if yes, go to 5
								my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE perc_indentity >= $identitySeqToSeq AND align_length >= $minOverlapSeqToSeq AND query = ? AND subject = ?");
								$getAlignment->execute($preSeq,$eachFpcSeq);
								if($getAlignment->rows > 0)
								{
									#5 merge two contigs;
									my $assemblyPreCtg=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
									$assemblyPreCtg->execute($assemblySeqCtgId->{$preSeq});
									my @assemblyPreCtg = $assemblyPreCtg->fetchrow_array();
									my $assemblyCurrentCtg=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
									$assemblyCurrentCtg->execute($assemblySeqCtgId->{$eachFpcSeq});
									my @assemblyCurrentCtg = $assemblyCurrentCtg->fetchrow_array();
									my $mergedName = ($assemblyPreCtg[2] < $assemblyCurrentCtg[2]) ? $assemblyPreCtg[2] : $assemblyCurrentCtg[2];
									my $mergedAssemblySeq = "$assemblyPreCtg[8],$assemblyCurrentCtg[8]";
									foreach (split ",", $mergedAssemblySeq)
									{
										next unless ($_);
										$_ =~ s/[^a-zA-Z0-9]//g;
										my $assemblySeq = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
										$assemblySeq->execute($_);
										my @assemblySeq = $assemblySeq->fetchrow_array();
										$assemblySeqCtg->{$assemblySeq[5]} = $mergedName;
										$assemblySeqCtgId->{$assemblySeq[5]} = $assemblyPreCtg[0];
									}
									my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET name = ?, note = ? WHERE id = ?");
									$updatedAssemblyCtg->execute($mergedName,$mergedAssemblySeq,$assemblyPreCtg[0]);
									my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $assemblyCurrentCtg[0]");
								}
							}
							$preSeq = $eachFpcSeq;
						}
					}
				}
			}
			elsif($fpcOrAgp[1] eq 'agp')
			{
				my $component;
				my $partNumber = -1;
				my $preAssemblyCtgId = 0;
				foreach (split "\n", $fpcOrAgp[8])
				{
					/^#/ and next;
					my @agpLine = split/\t/, $_;
				    if ($agpLine[4] ne 'N' && $agpLine[4] ne 'U' )
					{
						if (exists $component->{$agpLine[5]})
						{							
							#a component can't be used twice or more.
							$partNumber = $agpLine[3];
							next;
						}
						else
						{
							#set assemblySeq orientation based on $agpLine[8] and range based on "$agpLine[6]&$agpLine[7]"
							my $agpOrientation = ($agpLine[8] ne '-') ?  "1" : "-1";
							my $assemblySeqByName = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblySeq' AND o = ? AND name LIKE ?");
							$assemblySeqByName->execute($assemblyId,$agpLine[5]);
							my @assemblySeqByName = $assemblySeqByName->fetchrow_array();
							my $updateAssemblySeq=$dbh->prepare("UPDATE matrix SET barcode = ?, note = ? WHERE id = ?");
							$updateAssemblySeq->execute($agpOrientation,"$agpLine[6],$agpLine[7]",$assemblySeqByName[0]);
							if ($agpLine[3] - $partNumber == 1) #connected
							{
								#merge pre and current assemblyCtg
								unless($assemblySeqCtgId->{$assemblySeqByName[5]} == $preAssemblyCtgId)
								{
									my $assemblyPreCtg=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
									$assemblyPreCtg->execute($preAssemblyCtgId);
									my @assemblyPreCtg = $assemblyPreCtg->fetchrow_array();
									my $assemblyCurrentCtg=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
									$assemblyCurrentCtg->execute($assemblySeqCtgId->{$assemblySeqByName[5]});
									my @assemblyCurrentCtg = $assemblyCurrentCtg->fetchrow_array();
									my $mergedName = ($assemblyPreCtg[2] < $assemblyCurrentCtg[2]) ? $assemblyPreCtg[2] : $assemblyCurrentCtg[2];
									my $mergedAssemblySeq = "$assemblyPreCtg[8],$assemblyCurrentCtg[8]";
									foreach (split ",", $mergedAssemblySeq)
									{
										next unless ($_);
										$_ =~ s/[^a-zA-Z0-9]//g;
										my $assemblySeq = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
										$assemblySeq->execute($_);
										my @assemblySeq = $assemblySeq->fetchrow_array();
										$assemblySeqCtg->{$assemblySeq[5]} = $mergedName;
										$assemblySeqCtgId->{$assemblySeq[5]} = $assemblyPreCtg[0];
									}
									my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET name = ?, note = ? WHERE id = ?");
									$updatedAssemblyCtg->execute($mergedName,$mergedAssemblySeq,$assemblyPreCtg[0]);
									my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $assemblyCurrentCtg[0]");
								}
							}
							else
							{
								unless($fpcOrAgp[5] != 1) # Chr-Seq
								{
									#set assemblyCtg position based on $agpLine[1] and chrNumber based on $agpLine[0]
									($agpLine[0] =~ /^ChrUN/) and next;
									($agpLine[0] =~ /^Ctg/) and next;
									my $chrNumber = ($agpLine[0] =~ /(\d+)/) ? $1 : 0;
									my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET x = ?, z = ? WHERE id = ?");
									$updatedAssemblyCtg->execute($chrNumber,$agpLine[1],$assemblySeqCtgId->{$assemblySeqByName[5]});
								}
								# Ctg-Seq or unknown, no chrNumber and position assigned
								#do nothing
								$preAssemblyCtgId = $assemblySeqCtgId->{$assemblySeqByName[5]};
							}
							$partNumber = $agpLine[3];
							$component->{$agpLine[5]} = 1;
						}
					}
				}
			}
			my $updateAssemblyToRunningStatus=$dbh->do("UPDATE matrix SET barcode = '-1' WHERE id = $assemblyId");
		}

		if($refGenomeId)
		{
			my $updateAssemblyGenomeId=$dbh->do("UPDATE matrix SET y = $refGenomeId WHERE id = $assemblyId");

			my $hasAlignmentSequenceId;
			my $sequenceInRefGenome;
			open (GENOME,">/tmp/$refGenomeId.$$.genome") or die "can't open file: /tmp/$refGenomeId.$$.genome";
			my $getGenome = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = ?");
			$getGenome->execute($refGenomeId);
			while(my @getGenome = $getGenome->fetchrow_array())
			{
				$sequenceInRefGenome->{$getGenome[0]} = $getGenome[6];
				my $sequenceDetails = decode_json $getGenome[8];
				$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
				$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
				$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
				$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
				print GENOME ">$getGenome[0]\n$sequenceDetails->{'sequence'}\n";
				my $alignmentChecker = $dbh->prepare("SELECT query FROM alignment WHERE subject = ? GROUP BY query");
				$alignmentChecker->execute($getGenome[0]);
				while(my @alignmentChecker = $alignmentChecker->fetchrow_array())
				{
					$hasAlignmentSequenceId->{$alignmentChecker[0]} = 1;
				}
			}
			close(GENOME);
			
			if($alignEngine eq 'blastn')
			{
				if($softMasking)
				{
					system( "$windowmasker -in /tmp/$refGenomeId.$$.genome -infmt fasta -mk_counts -parse_seqids -out /tmp/$refGenomeId.$$.genome_mask.counts" );
					system( "$windowmasker -in /tmp/$refGenomeId.$$.genome -infmt fasta -ustat /tmp/$refGenomeId.$$.genome_mask.counts -outfmt maskinfo_asn1_bin -parse_seqids -out /tmp/$refGenomeId.$$.genome_mask.asnb" );
					system( "$makeblastdb -in /tmp/$refGenomeId.$$.genome -inputtype fasta -dbtype nucl -parse_seqids -mask_data /tmp/$refGenomeId.$$.genome_mask.asnb" );
				}
				else
				{
					system( "$makeblastdb -in /tmp/$refGenomeId.$$.genome -dbtype nucl" );
				}
			}
			
			if($seqToGenome)
			{
				my $updateAssemblyToRunningSeqToGenome=$dbh->do("UPDATE matrix SET barcode = '-4' WHERE id = '$assemblyId'");

				open (SEQALL,">/tmp/$assembly[4].$$.seq") or die "can't open file: /tmp/$assembly[4].$$.seq";
				open (SEQNEW,">/tmp/$assembly[4].$$.new.seq") or die "can't open file: /tmp/$assembly[4].$$.new.seq";
				if($target[1] eq 'library')
				{
					my $getClones = $dbh->prepare("SELECT * FROM clones WHERE sequenced > 0 AND libraryId = ?");
					$getClones->execute($assembly[4]);
					while(my @getClones = $getClones->fetchrow_array())
					{
						my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o < 50 AND name LIKE ?");
						$getSequences->execute($getClones[1]);
						while(my @getSequences = $getSequences->fetchrow_array())
						{
							my $sequenceDetails = decode_json $getSequences[8];
							$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
							$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
							$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
							$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
							print SEQALL ">$getSequences[0]\n$sequenceDetails->{'sequence'}\n";
							print SEQNEW ">$getSequences[0]\n$sequenceDetails->{'sequence'}\n" if (!exists $hasAlignmentSequenceId->{$getSequences[0]});
						}
					}
				}
				if($target[1] eq 'genome')
				{
					my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = ?");
					$getSequences->execute($assembly[4]);
					while(my @getSequences = $getSequences->fetchrow_array())
					{
						my $sequenceDetails = decode_json $getSequences[8];
						$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
						$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
						$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
						$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
						print SEQALL ">$getSequences[0]\n$sequenceDetails->{'sequence'}\n";
						print SEQNEW ">$getSequences[0]\n$sequenceDetails->{'sequence'}\n" if (!exists $hasAlignmentSequenceId->{$getSequences[0]});
					}
				}
				close(SEQALL);
				close(SEQNEW);
				my $newSeqToGenomeFound;
				if($redoAllSeqToGenome)
				{
					if($alignEngine eq 'blastn')
					{
						if($softMasking)
						{
							open (CMD,"$alignEngineList->{$alignEngine} -query /tmp/$assembly[4].$$.seq -task $task -db /tmp/$refGenomeId.$$.genome -db_soft_mask 30 -evalue 1e-200 -perc_identity $identitySeqToGenome -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
						}
						else
						{
							open (CMD,"$alignEngineList->{$alignEngine} -query /tmp/$assembly[4].$$.seq -task $task -db /tmp/$refGenomeId.$$.genome -evalue 1e-200 -perc_identity $identitySeqToGenome -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
						}
					}
					else
					{
						open (CMD,"$alignEngineList->{$alignEngine} /tmp/$refGenomeId.$$.genome /tmp/$assembly[4].$$.seq -out=blast8 -minIdentity=$identitySeqToGenome |") or die "can't open CMD: $!";
					}
				}
				else
				{
					if($alignEngine eq 'blastn')
					{
						if($softMasking)
						{
							open (CMD,"$alignEngineList->{$alignEngine} -query /tmp/$assembly[4].$$.new.seq -task $task -db /tmp/$refGenomeId.$$.genome -db_soft_mask 30 -evalue 1e-200 -perc_identity $identitySeqToGenome -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
						}
						else
						{
							open (CMD,"$alignEngineList->{$alignEngine} -query /tmp/$assembly[4].$$.new.seq -task $task -db /tmp/$refGenomeId.$$.genome -evalue 1e-200 -perc_identity $identitySeqToGenome -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
						}
					}
					else
					{
						open (CMD,"$alignEngineList->{$alignEngine} /tmp/$refGenomeId.$$.genome /tmp/$assembly[4].$$.new.seq -out=blast8 -minIdentity=$identitySeqToGenome |") or die "can't open CMD: $!";
					}
			
				}
				while(<CMD>)
				{
					/^#/ and next;
					my @hit = split("\t",$_);
					next if($hit[3] < $minOverlapSeqToGenome);
					my $newSeqToGenome = "BAC$hit[0]GNM$hit[1]";
					if (!exists $newSeqToGenomeFound->{$newSeqToGenome})
					{
						my $deleteAlignment = $dbh->prepare("DELETE FROM alignment WHERE query = ? AND subject = ?");
						$deleteAlignment->execute($hit[0],$hit[1]);
						$newSeqToGenomeFound->{$newSeqToGenome} = 1;
					}
					#write to alignment
					my $insertAlignment=$dbh->prepare("INSERT INTO alignment VALUES ('', 'SEQtoGNM\_$refGenomeId\_1e-200\_$identitySeqToGenome\_$minOverlapSeqToGenome', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)");
					$insertAlignment->execute(@hit);
				
				}
				close(CMD);
				unlink("/tmp/$assembly[4].$$.seq");
				unlink("/tmp/$assembly[4].$$.new.seq");
				if ($markRepeatRegion)
				{
					my $converageCutoff = 0.95;
					my $todo = 1;
					do{
						$todo = 0;
						my $lastQuery = 0;
						my $lastQend = 0;
						my $lastAlignmentLength = 0;
						my $lastAlignmentId = 0;
						my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE program = 'SEQtoGNM\_$refGenomeId\_1e-200\_$identitySeqToGenome\_$minOverlapSeqToGenome' AND hidden = 0 ORDER BY query,q_start,q_end");
						$getAlignment->execute();
						while (my @getAlignment = $getAlignment->fetchrow_array())
						{
							if($lastQuery == $getAlignment[2])
							{
								if($lastQend > $getAlignment[8])
								{
									my $converage = $lastQend - $getAlignment[8];
									if ( $converage/$lastAlignmentLength >= $converageCutoff)
									{
										my $hideLastAlignment=$dbh->do("UPDATE alignment SET hidden = 1 WHERE id = $lastAlignmentId");
										$todo = 1;
									}
									if ( $converage/$getAlignment[5] >= $converageCutoff)
									{
										my $hideAlignment=$dbh->do("UPDATE alignment SET hidden = 1 WHERE id = $getAlignment[0]");
										$todo = 1;
									}
								}
							}
							$lastQuery = $getAlignment[2];
							$lastQend = $getAlignment[9];
							$lastAlignmentLength = $getAlignment[5];
							$lastAlignmentId = $getAlignment[0];
						}
					} while($todo);
				}
				my $updateAssemblyToRunningStatus=$dbh->do("UPDATE matrix SET barcode = '-1' WHERE id = $assemblyId");
			}
			unlink("/tmp/$refGenomeId.$$.genome");
			unlink("/tmp/$refGenomeId.$$.genome.nhr");
			unlink("/tmp/$refGenomeId.$$.genome.nin");
			unlink("/tmp/$refGenomeId.$$.genome.nsq");
			`rm $commoncfg->{TMPDIR}/*.aln.html`; #delete cached files
			
			if($assignChr)
			{
				my $updateAssemblyToAssignChr=$dbh->do("UPDATE matrix SET barcode = '-5' WHERE id = $assemblyId");
				#assign ctg to genome chr
				my $assemblyAllCtgList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ?");
				$assemblyAllCtgList->execute($assemblyId);
				while (my @assemblyAllCtgList = $assemblyAllCtgList->fetchrow_array())
				{
					my $chrNumber;
					my $chrPosition;
					my $ctgAllSeqLength;
					for (split ",", $assemblyAllCtgList[8])
					{
						next unless ($_);
						$_ =~ s/[^a-zA-Z0-9]//g;
						$ctgAllSeqLength += $assemblySequenceLength->{$_};
						my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE hidden = 0 AND query = ? ORDER BY alignment.id");
						$getAlignment->execute($assemblySequenceId->{$_});
						while (my @getAlignment = $getAlignment->fetchrow_array())
						{
							next unless (exists $sequenceInRefGenome->{$getAlignment[3]}); #check if subject is in refGenome
							$chrNumber->{$sequenceInRefGenome->{$getAlignment[3]}} = 0 unless (exists $chrNumber->{$sequenceInRefGenome->{$getAlignment[3]}});
							$chrNumber->{$sequenceInRefGenome->{$getAlignment[3]}} += $getAlignment[5];
							$chrPosition->{$sequenceInRefGenome->{$getAlignment[3]}} = "$getAlignment[10]-$getAlignment[11]" unless (exists $chrPosition->{$sequenceInRefGenome->{$getAlignment[3]}});
							$chrPosition->{$sequenceInRefGenome->{$getAlignment[3]}} .= ",$getAlignment[10]-$getAlignment[11]" if ($chrPosition->{$sequenceInRefGenome->{$getAlignment[3]}} ne "$getAlignment[10]-$getAlignment[11]");
						}
					}
					my @assignedChr = sort {$chrNumber->{$b} <=> $chrNumber->{$a}} keys %$chrNumber;
					my $assignedChr = (@assignedChr) ? shift @assignedChr : 0;
					my $assignedPosition = 0;
					if($assignedChr)
					{
						my $occupiedKeyPoint;
						for (split ",",$chrPosition->{$assignedChr})
						{
							my ($start, $end) = split "-",$_;
							if($start < $end)
							{
								$occupiedKeyPoint->{$start} = $end unless (exists $occupiedKeyPoint->{$start});
								$occupiedKeyPoint->{$start} = $end if ($occupiedKeyPoint->{$start} < $end);
							}
							else
							{
								$occupiedKeyPoint->{$end} = $start unless (exists $occupiedKeyPoint->{$end});
								$occupiedKeyPoint->{$end} = $start if ($occupiedKeyPoint->{$end} < $start);
							}
						}
						my @occupiedKeyPoint = sort {$a <=> $b} keys %$occupiedKeyPoint;
						my $preKeyPoint = shift @occupiedKeyPoint;
						for (@occupiedKeyPoint) #merge overlapped alignments
						{
							if($_ < $occupiedKeyPoint->{$preKeyPoint})
							{
								$occupiedKeyPoint->{$preKeyPoint} = $occupiedKeyPoint->{$_} if($occupiedKeyPoint->{$_} > $occupiedKeyPoint->{$preKeyPoint});
								delete $occupiedKeyPoint->{$_};
							}
							else
							{
								$preKeyPoint = $_;
							}
						}
						@occupiedKeyPoint = sort {$a <=> $b} keys %$occupiedKeyPoint;
						my $maxCounts = 0;
						do
						{
							my $currentKeyPoint = shift @occupiedKeyPoint;
							my $positionCounts = $occupiedKeyPoint->{$currentKeyPoint} - $currentKeyPoint + 1;
						
							for (@occupiedKeyPoint)
							{
								$positionCounts += $occupiedKeyPoint->{$_} - $_ + 1 if($_ > $occupiedKeyPoint->{$currentKeyPoint} && $_ < $currentKeyPoint + $ctgAllSeqLength);
							}

							if ($positionCounts > $maxCounts)
							{
								$assignedPosition = $currentKeyPoint ;
								$maxCounts = $positionCounts;
							}
						}while(@occupiedKeyPoint);
					}
					my $updateAssemblyCtg=$dbh->do("UPDATE matrix SET x = $assignedChr, z = $assignedPosition WHERE id = $assemblyAllCtgList[0]");
				}
				my $updateAssemblyToRunningStatus=$dbh->do("UPDATE matrix SET barcode = '-1' WHERE id = $assemblyId");
			}
		}

		if($redundancyFilterSeq)
		{
			my $updateAssemblyToFilteringSeq=$dbh->do("UPDATE matrix SET barcode = '-6' WHERE id = $assemblyId");
			my $assemblyMultiCtgList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? AND note LIKE '%,%'");
			$assemblyMultiCtgList->execute($assemblyId);
			while (my @assemblyMultiCtgList = $assemblyMultiCtgList->fetchrow_array())
			{
				#buried seq
				my $todo = 1;
				do{
					$todo = 0;
					my @seqInCtg;
					foreach (split ",", $assemblyMultiCtgList[8])
					{
						next unless ($_);
						/^-/ and next;
						$_ =~ s/[^a-zA-Z0-9]//g;
						push @seqInCtg,$_;
					}
					my $totalSeqInCtg = @seqInCtg;
					for (my $i = 1; $i < $totalSeqInCtg; $i++)
					{
						my $startFound = 0;
						my $endFound = 0;
						my $coveredLength = 0;
						if($assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i-1]}} <= $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i]}})
						{
							my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE query = ? AND subject = ? ORDER BY id");
							$getAlignment->execute($assemblySequenceId->{$seqInCtg[$i-1]},$assemblySequenceId->{$seqInCtg[$i]});
							while (my @getAlignment = $getAlignment->fetchrow_array())
							{
								$startFound = 1 if ($getAlignment[8] == 1);
								$endFound = 1 if ($getAlignment[9] == $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i-1]}});
								$coveredLength += $getAlignment[9] - $getAlignment[8] + 1;
							}
							if ($startFound > 0 && $endFound > 0 && $coveredLength / $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i-1]}} >= 0.99)
							{
								$assemblyMultiCtgList[8] =~ s/\($seqInCtg[$i-1]\)/-($seqInCtg[$i-1])/g;
								my $updateAssemblyCtgNote=$dbh->do("UPDATE matrix SET note = '$assemblyMultiCtgList[8]' WHERE id = $assemblyMultiCtgList[0]");
								$todo = 1;
								$redundancySeq++;
							}
						}
						else
						{
							my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE query = ? AND subject = ? ORDER BY id");
							$getAlignment->execute($assemblySequenceId->{$seqInCtg[$i]},$assemblySequenceId->{$seqInCtg[$i-1]});
							while (my @getAlignment = $getAlignment->fetchrow_array())
							{
								$startFound = 1 if ($getAlignment[8] == 1);
								$endFound = 1 if ($getAlignment[9] == $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i]}});
								$coveredLength += $getAlignment[9] - $getAlignment[8] + 1;
							}
							if ($startFound > 0 && $endFound > 0 && $coveredLength / $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i]}} >= 0.99)
							{
								$assemblyMultiCtgList[8] =~ s/\($seqInCtg[$i]\)/-($seqInCtg[$i])/g;
								my $updateAssemblyCtgNote=$dbh->do("UPDATE matrix SET note = '$assemblyMultiCtgList[8]' WHERE id = $assemblyMultiCtgList[0]");
								$todo = 1;
								$redundancySeq++;
							}
						}
					}
				} while ($todo);

				#redundant seq (covered by pre and next seqs)
				$todo = 1;
				do{
					$todo = 0;
					my @seqInCtg;
					foreach (split ",", $assemblyMultiCtgList[8])
					{
						next unless ($_);
						/^-/ and next;
						$_ =~ s/[^a-zA-Z0-9]//g;
						push @seqInCtg,$_;
					}
					my $totalSeqInCtg = @seqInCtg;
					for (my $i = 1; $i < $totalSeqInCtg - 1; $i++)
					{
						my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE query = ? AND subject = ? ORDER BY id");
						$getAlignment->execute($assemblySequenceId->{$seqInCtg[$i-1]},$assemblySequenceId->{$seqInCtg[$i+1]});
						if ($getAlignment->rows > 0)
						{
							my $goodEndFound = 0;
							while (my @getAlignment = $getAlignment->fetchrow_array())
							{
								if($getAlignment[10] < $getAlignment[11])
								{
									$goodEndFound = 1 if ($getAlignment[8] == 1 || $getAlignment[9] == $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i-1]}} || $getAlignment[10] == 1 || $getAlignment[11] == $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i+1]}});
								}
								else
								{
									$goodEndFound = 1 if ($getAlignment[8] == 1 || $getAlignment[9] == $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i-1]}} || $getAlignment[10] == $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i+1]}} || $getAlignment[11] == 1);
								}
							}
							if($goodEndFound)
							{
								my $startFound = 0;
								my $endFound = 0;
								my $coveredLength = 0;
								my $getAlignmentPre = $dbh->prepare("SELECT * FROM alignment WHERE query = ? AND subject = ? ORDER BY id");
								$getAlignmentPre->execute($assemblySequenceId->{$seqInCtg[$i]},$assemblySequenceId->{$seqInCtg[$i-1]});
								while (my @getAlignmentPre = $getAlignmentPre->fetchrow_array())
								{
									$startFound = 1 if ($getAlignmentPre[8] == 1);
									$endFound = 1 if ($getAlignmentPre[9] == $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i]}});
									$coveredLength += $getAlignmentPre[9] - $getAlignmentPre[8] + 1;
								}
								my $getAlignmentNext = $dbh->prepare("SELECT * FROM alignment WHERE query = ? AND subject = ? ORDER BY id");
								$getAlignmentNext->execute($assemblySequenceId->{$seqInCtg[$i]},$assemblySequenceId->{$seqInCtg[$i+1]});
								while (my @getAlignmentNext = $getAlignmentNext->fetchrow_array())
								{
									$startFound = 1 if ($getAlignmentNext[8] == 1);
									$endFound = 1 if ($getAlignmentNext[9] == $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i]}});
									$coveredLength += $getAlignmentNext[9] - $getAlignmentNext[8] + 1;
								}

								if ($startFound > 0 && $endFound > 0 && $coveredLength / $assemblySequenceLength->{$assemblySequenceId->{$seqInCtg[$i]}} > 1)
								{
									$assemblyMultiCtgList[8] =~ s/\($seqInCtg[$i]\)/-($seqInCtg[$i])/g;
									my $updateAssemblyCtgNote=$dbh->do("UPDATE matrix SET note = '$assemblyMultiCtgList[8]' WHERE id = $assemblyMultiCtgList[0]");
									$todo = 1;
									$redundancySeq++;
								}
							}
						}
						$i = $totalSeqInCtg if ($todo);
					}
				} while ($todo);
			}
			my $updateAssemblyToRunningStatus=$dbh->do("UPDATE matrix SET barcode = '-1' WHERE id = $assemblyId");
		}

		if($orientSeqs)
		{
			my $updateAssemblyToAutoOrientation=$dbh->do("UPDATE matrix SET barcode = '-7' WHERE id = $assemblyId");
			my $assemblyMultiCtgList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? AND note LIKE '%,%'");
			$assemblyMultiCtgList->execute($assemblyId);
			while (my @assemblyMultiCtgList = $assemblyMultiCtgList->fetchrow_array())
			{
				my @seqInCtg;
				foreach (split ",", $assemblyMultiCtgList[8])
				{
					next unless ($_);
					/^-/ and next;
					$_ =~ s/[^a-zA-Z0-9]//g;						
					push @seqInCtg,$_;
				}
				next if (@seqInCtg < 2);
				#determine orientation based on ends
				my $orientation;
				my $preAssemblySeqId = shift @seqInCtg;
				$orientation->{$preAssemblySeqId} = 1;
				my $firstAssemblySeqFlag = 1;
				for my $currentAssemblySeqId (@seqInCtg)
				{
					#determine orientation based on ends
					my $preAssemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$preAssemblySeq->execute($preAssemblySeqId);
					my @preAssemblySeq = $preAssemblySeq->fetchrow_array();
					my $currentAssemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$currentAssemblySeq->execute($currentAssemblySeqId);
					my @currentAssemblySeq = $currentAssemblySeq->fetchrow_array();

					my $twoSeqDirection;
					my $getAlignmentTwo = $dbh->prepare("SELECT * FROM alignment WHERE perc_indentity >= $identityEndToEnd AND align_length >= $minOverlapEndToEnd AND query = ? AND subject = ?");
					$getAlignmentTwo->execute($preAssemblySeq[5],$currentAssemblySeq[5]);
					while (my @getAlignmentTwo = $getAlignmentTwo->fetchrow_array())
					{
						unless(exists $twoSeqDirection->{$preAssemblySeq[5]}->{$currentAssemblySeq[5]})
						{
							$twoSeqDirection->{$preAssemblySeq[5]}->{$currentAssemblySeq[5]} = ($getAlignmentTwo[10] < $getAlignmentTwo[11]) ? 1 : -1;
						}
						if($getAlignmentTwo[8] == 1)
						{
							$orientation->{$preAssemblySeqId} = -1;
							last;
						}
						if($getAlignmentTwo[9] == $preAssemblySeq[6])
						{
							$orientation->{$preAssemblySeqId} = 1;
							last;
						}
					}
					if ($firstAssemblySeqFlag)
					{
						my $updatePreAssemblySeq=$dbh->do("UPDATE matrix SET barcode = $orientation->{$preAssemblySeqId} WHERE id = $preAssemblySeqId");
						$firstAssemblySeqFlag = 0;
					}
					$twoSeqDirection->{$preAssemblySeq[5]}->{$currentAssemblySeq[5]} = 1 unless (exists $twoSeqDirection->{$preAssemblySeq[5]}->{$currentAssemblySeq[5]});
					$orientation->{$currentAssemblySeqId} = $orientation->{$preAssemblySeqId} * $twoSeqDirection->{$preAssemblySeq[5]}->{$currentAssemblySeq[5]};
					my $updateAssemblySeq=$dbh->do("UPDATE matrix SET barcode = $orientation->{$currentAssemblySeqId} WHERE id = $currentAssemblySeqId");
					$preAssemblySeqId = $currentAssemblySeqId;
				}
			}			
			my $updateAssemblyToRunningStatus=$dbh->do("UPDATE matrix SET barcode = '-1' WHERE id = $assemblyId");
		}

 		if ($refGenomeId && $orientContigs)
 		{
			my $updateAssemblyToOrientingContigs=$dbh->do("UPDATE matrix SET barcode = '-8' WHERE id = $assemblyId");
			my $assemblyAllCtgList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? ORDER BY x,z");
			$assemblyAllCtgList->execute($assemblyId);
			while (my @assemblyAllCtgList = $assemblyAllCtgList->fetchrow_array())
			{
				my $toBeFlipped = 0;
				for (split ",", $assemblyAllCtgList[8])
				{
					next unless ($_);
					/^-/ and next;
					$_ =~ s/[^a-zA-Z0-9]//g;						
					my $assemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$assemblySeq->execute($_);
					my @assemblySeq = $assemblySeq->fetchrow_array();
					my $alignmentToGenome = $dbh->prepare("SELECT * FROM matrix,alignment WHERE alignment.query = ? AND alignment.subject = matrix.id AND matrix.container LIKE 'sequence' AND matrix.o = 99 AND matrix.x = ? AND matrix.z = ? ORDER BY alignment.id");
					$alignmentToGenome->execute($assemblySeq[5],$refGenomeId,$assemblyAllCtgList[4]);
					while (my @alignmentToGenome = $alignmentToGenome->fetchrow_array())
					{
						if($assemblySeq[7] > 0)
						{
							if ($alignmentToGenome[21] > $alignmentToGenome[22])
							{
								$toBeFlipped += $alignmentToGenome[16];
							}
							else
							{
								$toBeFlipped -= $alignmentToGenome[16];
							}
						}
						else
						{
							if ($alignmentToGenome[21] < $alignmentToGenome[22])
							{
								$toBeFlipped += $alignmentToGenome[16];
							}
							else
							{
								$toBeFlipped -= $alignmentToGenome[16];
							}
						}
					}
				}
				if ($toBeFlipped > 0)
				{
					$assemblyAllCtgList[8] = join ",", (reverse split ",", $assemblyAllCtgList[8]);
					foreach (split ",", $assemblyAllCtgList[8])
					{
						next unless ($_);
						$_ =~ s/[^a-zA-Z0-9]//g;
						my $updateAssemblySeq=$dbh->do("UPDATE matrix SET barcode = barcode * (-1) WHERE id = $_");
					}
					my $updateAssemblyCtg=$dbh->prepare("UPDATE matrix SET note = ? WHERE id = ?");
					$updateAssemblyCtg->execute($assemblyAllCtgList[8],$assemblyAllCtgList[0]);
				}
			}
			my $updateAssemblyToRunningStatus=$dbh->do("UPDATE matrix SET barcode = '-1' WHERE id = $assemblyId");
 	 	}

		# end-to-end merge
		if($endToEnd)
		{
			my $updateAssemblyToRunningEndToEnd=$dbh->do("UPDATE matrix SET barcode = '-9' WHERE id = $assemblyId");
			if($refGenomeId)
			{
				my $ctgSeq;
				my $assemblyCtgIdFromCtg;
				my $assemblyChr;
				my $preCtg = '';
				my $ctgToChr=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ?  ORDER BY x, y");
				$ctgToChr->execute($assemblyId);
				while (my @ctgToChr = $ctgToChr->fetchrow_array())
				{
					$ctgSeq->{$ctgToChr[2]}=$ctgToChr[8];
					$assemblyChr->{$ctgToChr[2]}=$ctgToChr[4];
					$assemblyCtgIdFromCtg->{$ctgToChr[2]}=$ctgToChr[0];
					my $setPreCtg = 1;
					if ($preCtg && $assemblyChr->{$preCtg}==$assemblyChr->{$ctgToChr[2]})
					{
						my @preSeqList=split ",", $ctgSeq->{$preCtg};
						my $preCtgSeqId = '';
						for (@preSeqList)
						{
							next unless ($_);
							next if ($_ =~ /^-/);
							$_ =~ s/[^a-zA-Z0-9]//g;
							$preCtgSeqId = $_;
						}
						my $preCtgSeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$preCtgSeq->execute($preCtgSeqId);
						my @preCtgSeq = $preCtgSeq->fetchrow_array();
					  
						my @currentSeqList=split ",", $ctgSeq->{$ctgToChr[2]};
						my $currentCtgSeqId = '';
						for (@currentSeqList)
						{
							next unless ($_);
							next if ($_ =~ /^-/);
							$_ =~ s/[^a-zA-Z0-9]//g;
						 	$currentCtgSeqId = $_;
						 	last if ($currentCtgSeqId);
						}
						my $currentCtgSeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$currentCtgSeq->execute($currentCtgSeqId);
						my @currentCtgSeq = $currentCtgSeq->fetchrow_array();
					 
						my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE perc_indentity >= $identityEndToEnd AND align_length >= $minOverlapEndToEnd AND query = ? AND subject = ?");
						$getAlignment->execute($preCtgSeq[5],$currentCtgSeq[5]);
					 
						if($getAlignment->rows > 0)
						{
							my $goodEndFoundA = 0;
							my $goodEndFoundB = 0;
							while (my @getAlignment = $getAlignment->fetchrow_array())
							{
								$goodEndFoundA = 1 if ($getAlignment[8] == 1 || $getAlignment[9] == $preCtgSeq[6]);
								if($getAlignment[10] < $getAlignment[11])
								{
									$goodEndFoundB = 1 if ($getAlignment[10] == 1 || $getAlignment[11] == $currentCtgSeq[6]);
								}
								else
								{	
									 $goodEndFoundB = 1 if ($getAlignment[10] == $currentCtgSeq[6] || $getAlignment[11] == 1);
								}
							}

							if($goodEndFoundA && $goodEndFoundB)
							{
								if($preCtg < $ctgToChr[2])
								{
									$ctgSeq->{$preCtg} = "$ctgSeq->{$preCtg},$ctgSeq->{$ctgToChr[2]}";
									my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET name = ?, note = ? WHERE id = ?");
									$updatedAssemblyCtg->execute($preCtg,$ctgSeq->{$preCtg},$assemblyCtgIdFromCtg->{$preCtg});
									my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $assemblyCtgIdFromCtg->{$ctgToChr[2]}");
									delete $assemblyCtgIdFromCtg->{$ctgToChr[2]};       
									delete $ctgSeq->{$ctgToChr[2]};
									$setPreCtg = 0;
								 }
							   else
							   {
									$ctgSeq->{$ctgToChr[2]} = "$ctgSeq->{$preCtg},$ctgSeq->{$ctgToChr[2]}";
									my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET name = ?, note = ? WHERE id = ?");
									$updatedAssemblyCtg->execute($ctgToChr[2],$ctgSeq->{$ctgToChr[2]},$assemblyCtgIdFromCtg->{$ctgToChr[2]});
									my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $assemblyCtgIdFromCtg->{$preCtg}");
									delete $assemblyCtgIdFromCtg->{$preCtg};        
									delete $ctgSeq->{$preCtg};
							   }
							}
						}    
					}
					$preCtg=$ctgToChr[2] if ($setPreCtg);
				}
			}
			else
			{
				#merge singletons first
				my $singletonCtg;
				my $singletonCtgId;
				my $assemblySingletonCtgList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? AND note NOT LIKE '%,%'");
				$assemblySingletonCtgList->execute($assemblyId);
				while (my @assemblySingletonCtgList = $assemblySingletonCtgList->fetchrow_array())
				{
					next if ($assemblySingletonCtgList[8] =~ /^-/);
					$singletonCtg->{$assemblySingletonCtgList[2]} = $assemblySingletonCtgList[8];
					$singletonCtgId->{$assemblySingletonCtgList[2]} = $assemblySingletonCtgList[0];
				}
				my $merged;
				for my $eachSingletonCtgA (sort {$a <=> $b} keys %$singletonCtg)
				{
					next if (exists $merged->{$eachSingletonCtgA});
					$merged->{$eachSingletonCtgA} = 1;
					for my $eachSingletonCtgB (sort {$a <=> $b} keys %$singletonCtg)
					{
						next if (exists $merged->{$eachSingletonCtgB});
						my $singletonCtgSeqIdA = $singletonCtg->{$eachSingletonCtgA};
						$singletonCtgSeqIdA =~ s/[^a-zA-Z0-9]//g;
						my $eachSingletonCtgSeqA=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$eachSingletonCtgSeqA->execute($singletonCtgSeqIdA);
						my @eachSingletonCtgSeqA = $eachSingletonCtgSeqA->fetchrow_array();
						
						my $singletonCtgSeqIdB = $singletonCtg->{$eachSingletonCtgB};
						$singletonCtgSeqIdB =~ s/[^a-zA-Z0-9]//g;
						my $eachSingletonCtgSeqB=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$eachSingletonCtgSeqB->execute($singletonCtgSeqIdB);
						my @eachSingletonCtgSeqB = $eachSingletonCtgSeqB->fetchrow_array();

						my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE perc_indentity >= $identityEndToEnd AND align_length >= $minOverlapEndToEnd AND query = ? AND subject = ?");
						$getAlignment->execute($eachSingletonCtgSeqA[5],$eachSingletonCtgSeqB[5]);
						if($getAlignment->rows > 0)
						{
							my $goodEndFoundA = 0;
							my $goodEndFoundB = 0;
							while (my @getAlignment = $getAlignment->fetchrow_array())
							{
								$goodEndFoundA = 1 if ($getAlignment[8] == 1 || $getAlignment[9] == $eachSingletonCtgSeqA[6]);
								if($getAlignment[10] < $getAlignment[11])
								{
									$goodEndFoundB = 1 if ($getAlignment[10] == 1 || $getAlignment[11] == $eachSingletonCtgSeqB[6]);
								}
								else
								{
									$goodEndFoundB = 1 if ($getAlignment[10] == $eachSingletonCtgSeqB[6] || $getAlignment[11] == 1);
								}
							}

							if($goodEndFoundA && $goodEndFoundB)
							{
								my $mergedName = ($eachSingletonCtgA < $eachSingletonCtgB) ? $eachSingletonCtgA : $eachSingletonCtgB;
								my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET name = ?, note = ? WHERE id = ?");
								$updatedAssemblyCtg->execute($mergedName,"$singletonCtg->{$eachSingletonCtgA},$singletonCtg->{$eachSingletonCtgB}",$singletonCtgId->{$eachSingletonCtgA});
								my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $singletonCtgId->{$eachSingletonCtgB}");
								$merged->{$eachSingletonCtgB} = 1;
								delete $singletonCtg->{$eachSingletonCtgA};
								delete $singletonCtg->{$eachSingletonCtgB};
								delete $singletonCtgId->{$eachSingletonCtgA};
								delete $singletonCtgId->{$eachSingletonCtgB};
								last;
							}						
						}
					}
				}

				my $multiCtg;
				my $multiCtgId;
				my $assemblyMultiCtgList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? AND note LIKE '%,%'");
				$assemblyMultiCtgList->execute($assemblyId);
				while (my @assemblyMultiCtgList = $assemblyMultiCtgList->fetchrow_array())
				{
					$multiCtg->{$assemblyMultiCtgList[2]} = $assemblyMultiCtgList[8];
					$multiCtgId->{$assemblyMultiCtgList[2]} = $assemblyMultiCtgList[0];
				}

				#merge multies and singletons
				for my $eachSingletonCtg (sort {$a <=> $b} keys %$singletonCtg)
				{
					my $singletonCtgSeqId = $singletonCtg->{$eachSingletonCtg};
					$singletonCtgSeqId =~ s/[^a-zA-Z0-9]//g;
					my $eachSingletonCtgSeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$eachSingletonCtgSeq->execute($singletonCtgSeqId);
					my @eachSingletonCtgSeq = $eachSingletonCtgSeq->fetchrow_array();

					my $mergeFlag = 0;
					for my $eachMultiCtg (sort {$a <=> $b} keys %$multiCtg)
					{
						my $headSeqId = '';
						my $tailSeqId = '';
						for ( split ",", $multiCtg->{$eachMultiCtg})
						{
							next unless ($_);
							/^-/ and next;
							$_ =~ s/[^a-zA-Z0-9]//g;
							$headSeqId = $_ if ($headSeqId eq '');
							$tailSeqId = $_;
						}

						my $headCtgSeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$headCtgSeq->execute($headSeqId);
						my @headCtgSeq = $headCtgSeq->fetchrow_array();
						my $tailCtgSeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$tailCtgSeq->execute($tailSeqId);
						my @tailCtgSeq = $tailCtgSeq->fetchrow_array();

						my $getAlignmentHead = $dbh->prepare("SELECT * FROM alignment WHERE perc_indentity >= $identityEndToEnd AND align_length >= $minOverlapEndToEnd AND query = ? AND subject = ?");
						$getAlignmentHead->execute($eachSingletonCtgSeq[5],$headCtgSeq[5]);
						if($getAlignmentHead->rows > 0)
						{
							my $goodEndFoundA = 0;
							my $goodEndFoundB = 0;
							while (my @getAlignmentHead = $getAlignmentHead->fetchrow_array())
							{
								$goodEndFoundA = 1 if ($getAlignmentHead[8] == 1 || $getAlignmentHead[9] == $eachSingletonCtgSeq[6]);
								if($getAlignmentHead[10] < $getAlignmentHead[11])
								{
									$goodEndFoundB = 1 if ($getAlignmentHead[10] == 1 || $getAlignmentHead[11] == $headCtgSeq[6]);
								}
								else
								{
									$goodEndFoundB = 1 if ($getAlignmentHead[10] == $headCtgSeq[6] || $getAlignmentHead[11] == 1);
								}
							}

							if($goodEndFoundA && $goodEndFoundB)
							{
								my $mergedName = ($eachSingletonCtg < $eachMultiCtg) ? $eachSingletonCtg : $eachMultiCtg;
								$multiCtg->{$mergedName} = "$singletonCtg->{$eachSingletonCtg},$multiCtg->{$eachMultiCtg}";
								$multiCtgId->{$mergedName} = $multiCtgId->{$eachMultiCtg};
								my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET name = ?, note = ? WHERE id = ?");
								$updatedAssemblyCtg->execute($mergedName,$multiCtg->{$mergedName},$multiCtgId->{$mergedName});
								my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $singletonCtgId->{$eachSingletonCtg}");
								if ($eachSingletonCtg < $eachMultiCtg)
								{
									delete $multiCtg->{$eachMultiCtg};
									delete $multiCtgId->{$eachMultiCtg};
								}
								delete $singletonCtg->{$eachSingletonCtg};
								delete $singletonCtgId->{$eachSingletonCtg};
								$mergeFlag = 1;
								last;
							}
						}

						last if ($mergeFlag);
						next if ($tailSeqId == $headSeqId);

						my $getAlignmentTail = $dbh->prepare("SELECT * FROM alignment WHERE perc_indentity >= $identityEndToEnd AND align_length >= $minOverlapEndToEnd AND query = ? AND subject = ?");
						$getAlignmentTail->execute($eachSingletonCtgSeq[5],$tailCtgSeq[5]);
						if($getAlignmentTail->rows > 0)
						{
							my $goodEndFoundA = 0;
							my $goodEndFoundB = 0;
							while (my @getAlignmentTail = $getAlignmentTail->fetchrow_array())
							{
								$goodEndFoundA = 1 if ($getAlignmentTail[8] == 1 || $getAlignmentTail[9] == $eachSingletonCtgSeq[6]);
								if($getAlignmentTail[10] < $getAlignmentTail[11])
								{
									$goodEndFoundB = 1 if ($getAlignmentTail[10] == 1 || $getAlignmentTail[11] == $tailCtgSeq[6]);
								}
								else
								{
									$goodEndFoundB = 1 if ($getAlignmentTail[10] == $tailCtgSeq[6] || $getAlignmentTail[11] == 1);
								}
							}

							if($goodEndFoundA && $goodEndFoundB)
							{
								my $mergedName = ($eachSingletonCtg < $eachMultiCtg) ? $eachSingletonCtg : $eachMultiCtg;
								$multiCtg->{$mergedName} = "$multiCtg->{$eachMultiCtg},$singletonCtg->{$eachSingletonCtg}";
								$multiCtgId->{$mergedName} = $multiCtgId->{$eachMultiCtg};
								my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET name = ?, note = ? WHERE id = ?");
								$updatedAssemblyCtg->execute($mergedName,$multiCtg->{$mergedName},$multiCtgId->{$mergedName});
								my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $singletonCtgId->{$eachSingletonCtg}");
								if($eachSingletonCtg < $eachMultiCtg)
								{
									delete $multiCtgId->{$eachMultiCtg};								
									delete $multiCtg->{$eachMultiCtg};
								}
								delete $singletonCtg->{$eachSingletonCtg};
								delete $singletonCtgId->{$eachSingletonCtg};
								$mergeFlag = 1;									
								last;
							}
						}
						last if ($mergeFlag);
					}
				}
			
				#merge multies
				my $mergeMulties = 1;
				my $checkedCtg;
				do{
					my $mergeFlag = 0;
					for my $eachMultiCtgA (sort {$a <=> $b} keys %$multiCtg)
					{
						next if (exists $checkedCtg->{$eachMultiCtgA});
						$checkedCtg->{$eachMultiCtgA} = 1;

						my $headSeqIdA = '';
						my $tailSeqIdA = '';
						for ( split ",", $multiCtg->{$eachMultiCtgA})
						{
							next unless ($_);
							/^-/ and next;
							$_ =~ s/[^a-zA-Z0-9]//g;
							$headSeqIdA = $_ if ($headSeqIdA eq '');
							$tailSeqIdA = $_;
						}

						my $headCtgSeqA=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$headCtgSeqA->execute($headSeqIdA);
						my @headCtgSeqA = $headCtgSeqA->fetchrow_array();

						my $tailCtgSeqA=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$tailCtgSeqA->execute($tailSeqIdA);
						my @tailCtgSeqA = $tailCtgSeqA->fetchrow_array();

						for my $eachMultiCtgB (sort {$a <=> $b} keys %$multiCtg)
						{
							next if (exists $checkedCtg->{$eachMultiCtgB});

							my $headSeqIdB = '';
							my $tailSeqIdB = '';
							for ( split ",", $multiCtg->{$eachMultiCtgB})
							{
								next unless ($_);
								/^-/ and next;
								$_ =~ s/[^a-zA-Z0-9]//g;
								$headSeqIdB = $_ if ($headSeqIdB eq '');
								$tailSeqIdB = $_;
							}

							my $headCtgSeqB=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
							$headCtgSeqB->execute($headSeqIdB);
							my @headCtgSeqB = $headCtgSeqB->fetchrow_array();

							my $tailCtgSeqB=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
							$tailCtgSeqB->execute($tailSeqIdB);
							my @tailCtgSeqB = $tailCtgSeqB->fetchrow_array();

							my $getAlignmentAHBH = $dbh->prepare("SELECT * FROM alignment WHERE perc_indentity >= $identityEndToEnd AND align_length >= $minOverlapEndToEnd AND query = ? AND subject = ?");
							$getAlignmentAHBH->execute($headCtgSeqA[5],$headCtgSeqB[5]);
							if($getAlignmentAHBH->rows > 0)
							{
								my $goodEndFoundA = 0;
								my $goodEndFoundB = 0;
								while (my @getAlignmentAHBH = $getAlignmentAHBH->fetchrow_array())
								{
									$goodEndFoundA = 1 if ($getAlignmentAHBH[8] == 1 || $getAlignmentAHBH[9] == $headCtgSeqA[6]);
									if($getAlignmentAHBH[10] < $getAlignmentAHBH[11])
									{
										$goodEndFoundB = 1 if ($getAlignmentAHBH[10] == 1 || $getAlignmentAHBH[11] == $headCtgSeqB[6]);
									}
									else
									{
										$goodEndFoundB = 1 if ($getAlignmentAHBH[10] == $headCtgSeqB[6] || $getAlignmentAHBH[11] == 1);
									}
								}

								if($goodEndFoundA && $goodEndFoundB)
								{
									$multiCtg->{$eachMultiCtgA} = join ",", (reverse split ",", $multiCtg->{$eachMultiCtgA}); #flip ctgA
									foreach (split ",", $multiCtg->{$eachMultiCtgA})
									{
										next unless ($_);
										$_ =~ s/[^a-zA-Z0-9]//g;
										my $updateAssemblySeq=$dbh->do("UPDATE matrix SET barcode = barcode * (-1) WHERE id = $_");
									}
									if($eachMultiCtgA < $eachMultiCtgB)
									{
										$multiCtg->{$eachMultiCtgA} = "$multiCtg->{$eachMultiCtgA},$multiCtg->{$eachMultiCtgB}";
										my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET note = ? WHERE id = ?");
										$updatedAssemblyCtg->execute($multiCtg->{$eachMultiCtgA},$multiCtgId->{$eachMultiCtgA});
										my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $multiCtgId->{$eachMultiCtgB}");
										delete $multiCtgId->{$eachMultiCtgB};								
										delete $multiCtg->{$eachMultiCtgB};
									}
									else
									{
										$multiCtg->{$eachMultiCtgB} = "$multiCtg->{$eachMultiCtgA},$multiCtg->{$eachMultiCtgB}";
										my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET note = ? WHERE id = ?");
										$updatedAssemblyCtg->execute($multiCtg->{$eachMultiCtgB},$multiCtgId->{$eachMultiCtgB});
										my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $multiCtgId->{$eachMultiCtgA}");
										delete $multiCtgId->{$eachMultiCtgA};
										delete $multiCtg->{$eachMultiCtgA};
									}
									$mergeFlag = 1;
									last;
								}
							}
							last if($mergeFlag);

							my $getAlignmentAHBT = $dbh->prepare("SELECT * FROM alignment WHERE perc_indentity >= $identityEndToEnd AND align_length >= $minOverlapEndToEnd AND query = ? AND subject = ?");
							$getAlignmentAHBT->execute($headCtgSeqA[5],$tailCtgSeqB[5]);
							if($getAlignmentAHBT->rows > 0)
							{
								my $goodEndFoundA = 0;
								my $goodEndFoundB = 0;
								while (my @getAlignmentAHBT = $getAlignmentAHBT->fetchrow_array())
								{
									$goodEndFoundA = 1 if ($getAlignmentAHBT[8] == 1 || $getAlignmentAHBT[9] == $headCtgSeqA[6]);
									if($getAlignmentAHBT[10] < $getAlignmentAHBT[11])
									{
										$goodEndFoundB = 1 if ($getAlignmentAHBT[10] == 1 || $getAlignmentAHBT[11] == $tailCtgSeqB[6]);
									}
									else
									{
										$goodEndFoundB = 1 if ($getAlignmentAHBT[10] == $tailCtgSeqB[6] || $getAlignmentAHBT[11] == 1);
									}
								}

								if($goodEndFoundA && $goodEndFoundB)
								{
									if($eachMultiCtgA < $eachMultiCtgB)
									{
										$multiCtg->{$eachMultiCtgA} = "$multiCtg->{$eachMultiCtgB},$multiCtg->{$eachMultiCtgA}";
										my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET note = ? WHERE id = ?");
										$updatedAssemblyCtg->execute($multiCtg->{$eachMultiCtgA},$multiCtgId->{$eachMultiCtgA});
										my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $multiCtgId->{$eachMultiCtgB}");
										delete $multiCtgId->{$eachMultiCtgB};								
										delete $multiCtg->{$eachMultiCtgB};
									}
									else
									{
										$multiCtg->{$eachMultiCtgB} = "$multiCtg->{$eachMultiCtgB},$multiCtg->{$eachMultiCtgA}";
										my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET note = ? WHERE id = ?");
										$updatedAssemblyCtg->execute($multiCtg->{$eachMultiCtgB},$multiCtgId->{$eachMultiCtgB});
										my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $multiCtgId->{$eachMultiCtgA}");
										delete $multiCtgId->{$eachMultiCtgA};
										delete $multiCtg->{$eachMultiCtgA};
									}
									$mergeFlag = 1;
									last;
								}
							}

							last if($mergeFlag);

							my $getAlignmentATBH = $dbh->prepare("SELECT * FROM alignment WHERE perc_indentity >= $identityEndToEnd AND align_length >= $minOverlapEndToEnd AND query = ? AND subject = ?");
							$getAlignmentATBH->execute($tailCtgSeqA[5],$headCtgSeqB[5]);
							if($getAlignmentATBH->rows > 0)
							{
								my $goodEndFoundA = 0;
								my $goodEndFoundB = 0;
								while (my @getAlignmentATBH = $getAlignmentATBH->fetchrow_array())
								{
									$goodEndFoundA = 1 if ($getAlignmentATBH[8] == 1 || $getAlignmentATBH[9] == $tailCtgSeqA[6]);
									if($getAlignmentATBH[10] < $getAlignmentATBH[11])
									{
										$goodEndFoundB = 1 if ($getAlignmentATBH[10] == 1 || $getAlignmentATBH[11] == $headCtgSeqB[6]);
									}
									else
									{
										$goodEndFoundB = 1 if ($getAlignmentATBH[10] == $headCtgSeqB[6] || $getAlignmentATBH[11] == 1);
									}
								}

								if($goodEndFoundA && $goodEndFoundB)
								{
									if($eachMultiCtgA < $eachMultiCtgB)
									{
										$multiCtg->{$eachMultiCtgA} = "$multiCtg->{$eachMultiCtgA},$multiCtg->{$eachMultiCtgB}";
										my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET note = ? WHERE id = ?");
										$updatedAssemblyCtg->execute($multiCtg->{$eachMultiCtgA},$multiCtgId->{$eachMultiCtgA});
										my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $multiCtgId->{$eachMultiCtgB}");
										delete $multiCtgId->{$eachMultiCtgB};								
										delete $multiCtg->{$eachMultiCtgB};
									}
									else
									{
										$multiCtg->{$eachMultiCtgB} = "$multiCtg->{$eachMultiCtgA},$multiCtg->{$eachMultiCtgB}";
										my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET note = ? WHERE id = ?");
										$updatedAssemblyCtg->execute($multiCtg->{$eachMultiCtgB},$multiCtgId->{$eachMultiCtgB});
										my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $multiCtgId->{$eachMultiCtgA}");
										delete $multiCtgId->{$eachMultiCtgA};
										delete $multiCtg->{$eachMultiCtgA};
									}
									$mergeFlag = 1;
									last;
								}
							}
							last if($mergeFlag);

							my $getAlignmentATBT = $dbh->prepare("SELECT * FROM alignment WHERE perc_indentity >= $identityEndToEnd AND align_length >= $minOverlapEndToEnd AND query = ? AND subject = ?");
							$getAlignmentATBT->execute($tailCtgSeqA[5],$tailCtgSeqB[5]);
							if($getAlignmentATBT->rows > 0)
							{
								my $goodEndFoundA = 0;
								my $goodEndFoundB = 0;
								while (my @getAlignmentATBT = $getAlignmentATBT->fetchrow_array())
								{
									$goodEndFoundA = 1 if ($getAlignmentATBT[8] == 1 || $getAlignmentATBT[9] == $tailCtgSeqA[6]);
									if($getAlignmentATBT[10] < $getAlignmentATBT[11])
									{
										$goodEndFoundB = 1 if ($getAlignmentATBT[10] == 1 || $getAlignmentATBT[11] == $tailCtgSeqB[6]);
									}
									else
									{
										$goodEndFoundB = 1 if ($getAlignmentATBT[10] == $tailCtgSeqB[6] || $getAlignmentATBT[11] == 1);
									}
								}

								if($goodEndFoundA && $goodEndFoundB)
								{
									$multiCtg->{$eachMultiCtgB} = join ",", (reverse split ",", $multiCtg->{$eachMultiCtgB}); #flip ctgB
									foreach (split ",", $multiCtg->{$eachMultiCtgB})
									{
										next unless ($_);
										$_ =~ s/[^a-zA-Z0-9]//g;
										my $updateAssemblySeq=$dbh->do("UPDATE matrix SET barcode = barcode * (-1) WHERE id = $_");
									}
									if($eachMultiCtgA < $eachMultiCtgB)
									{
										$multiCtg->{$eachMultiCtgA} = "$multiCtg->{$eachMultiCtgA},$multiCtg->{$eachMultiCtgB}";
										my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET note = ? WHERE id = ?");
										$updatedAssemblyCtg->execute($multiCtg->{$eachMultiCtgA},$multiCtgId->{$eachMultiCtgA});
										my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $multiCtgId->{$eachMultiCtgB}");
										delete $multiCtgId->{$eachMultiCtgB};								
										delete $multiCtg->{$eachMultiCtgB};
									}
									else
									{
										$multiCtg->{$eachMultiCtgB} = "$multiCtg->{$eachMultiCtgA},$multiCtg->{$eachMultiCtgB}";
										my $updatedAssemblyCtg = $dbh->prepare("UPDATE matrix SET note = ? WHERE id = ?");
										$updatedAssemblyCtg->execute($multiCtg->{$eachMultiCtgB},$multiCtgId->{$eachMultiCtgB});
										my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $multiCtgId->{$eachMultiCtgA}");
										delete $multiCtgId->{$eachMultiCtgA};
										delete $multiCtg->{$eachMultiCtgA};
									}							
									$mergeFlag = 1;
									delete $checkedCtg->{$eachMultiCtgA};
									last;
								}
							}
							last if($mergeFlag);
						}
						delete $checkedCtg->{$eachMultiCtgA} if($mergeFlag);
						last if($mergeFlag);
					}
					unless($mergeFlag)
					{
						$mergeMulties = 0;
					}
				} while ($mergeMulties);

			}
			my $updateAssemblyToRunningStatus=$dbh->do("UPDATE matrix SET barcode = '-1' WHERE id = $assemblyId");
		}

		if($redundancyFilterOverlap)
		{
			my $updateAssemblyToFilteringOverlap=$dbh->do("UPDATE matrix SET barcode = '-10' WHERE id = $assemblyId");
			my $assemblyMultiCtgList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? AND note LIKE '%,%'");
			$assemblyMultiCtgList->execute($assemblyId);
			while (my @assemblyMultiCtgList = $assemblyMultiCtgList->fetchrow_array())
			{
				my @seqInCtg;
				foreach (split ",", $assemblyMultiCtgList[8])
				{
					next unless ($_);
					/^-/ and next;
					$_ =~ s/[^a-zA-Z0-9]//g;
					push @seqInCtg,$_;
				}
				my $totalSeqInCtg = @seqInCtg;
				for (@seqInCtg)
				{
					my $assemblySeqResetLength=$dbh->do("UPDATE matrix SET note = CONCAT('1,', z) WHERE id = $_");
				}
				for (my $i = 1; $i < $totalSeqInCtg; $i++)
				{
					my $preAssemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$preAssemblySeq->execute($seqInCtg[$i-1]);
					my @preAssemblySeq = $preAssemblySeq->fetchrow_array();
					my $preSeqStart;
					my $preSeqEnd;
					if($preAssemblySeq[8])
					{
						($preSeqStart,$preSeqEnd) = split ",",$preAssemblySeq[8];
					}
					else
					{
						$preSeqStart = 1;
						$preSeqEnd = $preAssemblySeq[6];
					}
					my $preSequence = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$preSequence->execute($preAssemblySeq[5]);
					my @preSequence = $preSequence->fetchrow_array();

					my $nextAssemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$nextAssemblySeq->execute($seqInCtg[$i]);
					my @nextAssemblySeq = $nextAssemblySeq->fetchrow_array();
					my $nextSeqStart;
					my $nextSeqEnd;
					if($nextAssemblySeq[8])
					{
						($nextSeqStart,$nextSeqEnd) = split ",",$nextAssemblySeq[8];
					}
					else
					{
						$nextSeqStart = 1;
						$nextSeqEnd = $nextAssemblySeq[6];
					}
					my $nextSequence = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$nextSequence->execute($nextAssemblySeq[5]);
					my @nextSequence = $nextSequence->fetchrow_array();

					my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE query = ? AND subject = ? ORDER BY id LIMIT 1");
					$getAlignment->execute($preAssemblySeq[5],$nextAssemblySeq[5]);
					my @getAlignment = $getAlignment->fetchrow_array();

					my $preSeqStartCandidate = $preSeqStart;
					my $preSeqEndCandidate = $preSeqEnd;
					my $nextSeqStartCandidate = $nextSeqStart;
					my $nextSeqEndCandidate = $nextSeqEnd;

					if($preSequence[3] < 4) #if preSeq has non-gapped sequence
					{
						#keep preSeq sequence
						if($preAssemblySeq[7] > 0)
						{
							if ($getAlignment[10] < $getAlignment[11])
							{
								$preSeqEndCandidate = $getAlignment[9];
								$nextSeqStartCandidate = $getAlignment[11] + 1;
							}
							else
							{
								$preSeqEndCandidate = $getAlignment[9];
								$nextSeqEndCandidate = $getAlignment[11] - 1;
							}
						}
						else
						{
							if ($getAlignment[10] < $getAlignment[11])
							{
								$preSeqStartCandidate = $getAlignment[8];
								$nextSeqEndCandidate = $getAlignment[10] - 1;
							}
							else
							{
								$preSeqStartCandidate = $getAlignment[8];
								$nextSeqStartCandidate = $getAlignment[10] + 1;
							}
						}

						if ($preSeqStartCandidate >= 1 && $preSeqEndCandidate <= $preAssemblySeq[6] && $nextSeqStartCandidate >= 1 && $nextSeqEndCandidate <= $nextAssemblySeq[6] && $preSeqStartCandidate <= $preSeqEndCandidate && $nextSeqStartCandidate <= $nextSeqEndCandidate)
						{
							my $updateAssemblySeqPre=$dbh->do("UPDATE matrix SET note = '$preSeqStartCandidate,$preSeqEndCandidate' WHERE id = $preAssemblySeq[0]");
							my $updateAssemblySeqNext=$dbh->do("UPDATE matrix SET note = '$nextSeqStartCandidate,$nextSeqEndCandidate' WHERE id = $nextAssemblySeq[0]");
						}
						else
						{
							#keep nextSeq sequence
							$preSeqStartCandidate = $preSeqStart;
							$preSeqEndCandidate = $preSeqEnd;
							$nextSeqStartCandidate = $nextSeqStart;
							$nextSeqEndCandidate = $nextSeqEnd;
							if($preAssemblySeq[7] > 0)
							{
								if ($getAlignment[10] < $getAlignment[11])
								{
									$preSeqEndCandidate = $getAlignment[8] - 1;
									$nextSeqStartCandidate = $getAlignment[10];
								}
								else
								{
									$preSeqEndCandidate = $getAlignment[8] - 1;
									$nextSeqEndCandidate = $getAlignment[10];
								}
							}
							else
							{
								if ($getAlignment[10] < $getAlignment[11])
								{
									$preSeqStartCandidate = $getAlignment[9] + 1;
									$nextSeqEndCandidate = $getAlignment[11];
								}
								else
								{
									$preSeqStartCandidate = $getAlignment[9] + 1;
									$nextSeqStartCandidate = $getAlignment[11];
								}
							}

							if ($preSeqStartCandidate >= 1 && $preSeqEndCandidate <= $preAssemblySeq[6] && $nextSeqStartCandidate >= 1 && $nextSeqEndCandidate <= $nextAssemblySeq[6] && $preSeqStartCandidate <= $preSeqEndCandidate && $nextSeqStartCandidate <= $nextSeqEndCandidate)
							{
								my $updateAssemblySeqPre=$dbh->do("UPDATE matrix SET note = '$preSeqStartCandidate,$preSeqEndCandidate' WHERE id = $preAssemblySeq[0]");
								my $updateAssemblySeqNext=$dbh->do("UPDATE matrix SET note = '$nextSeqStartCandidate,$nextSeqEndCandidate' WHERE id = $nextAssemblySeq[0]");
							}
							else
							{
								#do nothing if conflicts found
							}
						}
					}
					else
					{
						#keep nextSeq sequence
						if($preAssemblySeq[7] > 0)
						{
							if ($getAlignment[10] < $getAlignment[11])
							{
								$preSeqEndCandidate = $getAlignment[8] - 1;
								$nextSeqStartCandidate = $getAlignment[10];
							}
							else
							{
								$preSeqEndCandidate = $getAlignment[8] - 1;
								$nextSeqEndCandidate = $getAlignment[10];
							}
						}
						else
						{
							if ($getAlignment[10] < $getAlignment[11])
							{
								$preSeqStartCandidate = $getAlignment[9] + 1;
								$nextSeqEndCandidate = $getAlignment[11];
							}
							else
							{
								$preSeqStartCandidate = $getAlignment[9] + 1;
								$nextSeqStartCandidate = $getAlignment[11];
							}
						}

						if ($preSeqStartCandidate >= 1 && $preSeqEndCandidate <= $preAssemblySeq[6] && $nextSeqStartCandidate >= 1 && $nextSeqEndCandidate <= $nextAssemblySeq[6] && $preSeqStartCandidate <= $preSeqEndCandidate && $nextSeqStartCandidate <= $nextSeqEndCandidate)
						{
							my $updateAssemblySeqPre=$dbh->do("UPDATE matrix SET note = '$preSeqStartCandidate,$preSeqEndCandidate' WHERE id = $preAssemblySeq[0]");
							my $updateAssemblySeqNext=$dbh->do("UPDATE matrix SET note = '$nextSeqStartCandidate,$nextSeqEndCandidate' WHERE id = $nextAssemblySeq[0]");
						}
						else
						{
							$preSeqStartCandidate = $preSeqStart;
							$preSeqEndCandidate = $preSeqEnd;
							$nextSeqStartCandidate = $nextSeqStart;
							$nextSeqEndCandidate = $nextSeqEnd;
							#keep preSeq sequence
							if($preAssemblySeq[7] > 0)
							{
								if ($getAlignment[10] < $getAlignment[11])
								{
									$preSeqEndCandidate = $getAlignment[9];
									$nextSeqStartCandidate = $getAlignment[11] + 1;
								}
								else
								{
									$preSeqEndCandidate = $getAlignment[9];
									$nextSeqEndCandidate = $getAlignment[11] - 1;
								}
							}
							else
							{
								if ($getAlignment[10] < $getAlignment[11])
								{
									$preSeqStartCandidate = $getAlignment[8];
									$nextSeqEndCandidate = $getAlignment[10] - 1;
								}
								else
								{
									$preSeqStartCandidate = $getAlignment[8];
									$nextSeqStartCandidate = $getAlignment[10] + 1;
								}
							}

							if ($preSeqStartCandidate >= 1 && $preSeqEndCandidate <= $preAssemblySeq[6] && $nextSeqStartCandidate >= 1 && $nextSeqEndCandidate <= $nextAssemblySeq[6] && $preSeqStartCandidate <= $preSeqEndCandidate && $nextSeqStartCandidate <= $nextSeqEndCandidate)
							{
								my $updateAssemblySeqPre=$dbh->do("UPDATE matrix SET note = '$preSeqStartCandidate,$preSeqEndCandidate' WHERE id = $preAssemblySeq[0]");
								my $updateAssemblySeqNext=$dbh->do("UPDATE matrix SET note = '$nextSeqStartCandidate,$nextSeqEndCandidate' WHERE id = $nextAssemblySeq[0]");
							}
							else
							{
								#do nothing if conflicts found
							}
						}
					}
				}
			}
			my $updateAssemblyToRunningStatus=$dbh->do("UPDATE matrix SET barcode = '-1' WHERE id = $assemblyId");
		}

		my $updateAssemblyToEstimatingLength=$dbh->do("UPDATE matrix SET barcode = '-11' WHERE id = $assemblyId");
		my $assemblyAllCtgList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? ORDER BY x,z");
		$assemblyAllCtgList->execute($assemblyId);
		my $totalCtgNumber = $assemblyAllCtgList->rows;
		my $assignedChrOrder = 1;
		while (my @assemblyAllCtgList = $assemblyAllCtgList->fetchrow_array())
		{
			my $assemblyCtgLength = 0;
			my $assemblySeqList = '';

			my @assemblySeqListAll;
			my $firstAssemblySeq = "";
			my $lastAssemblySeq = "";
			
			foreach (split ",", $assemblyAllCtgList[8])
			{
				next unless ($_);
				$assemblySeqList .= ($assemblySeqList ne '') ? ",$_": $_;
				/^-/ and next;
				$_ =~ s/[^a-zA-Z0-9]//g;
				push @assemblySeqListAll, $_;
				$firstAssemblySeq = $_ unless ($firstAssemblySeq);
				$lastAssemblySeq = $_;
			}

			my $lastComponentType = '';
			for (@assemblySeqListAll)
			{
				my $assemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
				$assemblySeq->execute($_);
				my @assemblySeq = $assemblySeq->fetchrow_array();
				my $assemblySeqStart;
				my $assemblySeqEnd;
				if($assemblySeq[8])
				{
					($assemblySeqStart,$assemblySeqEnd) = split ",",$assemblySeq[8];
				}
				else
				{
					$assemblySeqStart = 1;
					$assemblySeqEnd = $assemblySeq[6];
					my $updateAssemblySeq=$dbh->do("UPDATE matrix SET note = '$assemblySeqStart,$assemblySeqEnd' WHERE id = $assemblySeq[0]");
				}
				my $filterLength = 0;
				my $sequence = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
				$sequence->execute($assemblySeq[5]);
				my @sequence =  $sequence->fetchrow_array();
				my $sequenceDetails = decode_json $sequence[8];
				$sequenceDetails->{'filter'} = '' unless (exists $sequenceDetails->{'filter'});
				if ($sequenceDetails->{'filter'}) 
				{
					foreach (split ",", $sequenceDetails->{'filter'} )
					{
						my ($filterStart,$filterEnd) = split "-", $_;
						next if ($assemblySeqStart > $filterEnd);
						next if ($assemblySeqEnd < $filterStart);
						if ($assemblySeqStart >= $filterStart && $assemblySeqEnd <= $filterEnd)
						{
							$filterLength += $assemblySeqEnd - $assemblySeqStart + 1;
						}
						elsif ($assemblySeqStart >= $filterStart && $assemblySeqStart <= $filterEnd)
						{
							$filterLength += $filterEnd - $assemblySeqStart + 1;
						}
						elsif ($assemblySeqEnd >= $filterStart && $assemblySeqEnd <= $filterEnd)
						{
							$filterLength += $assemblySeqEnd - $filterStart + 1;
						}
						else
						{
							$filterLength += $filterEnd - $filterStart + 1;
						}
					}
				}
				#add non-end gaps to assemblyCtg length
				if($_ ne $firstAssemblySeq && $lastComponentType ne 'U')
				{
					if ($assemblySeq[4] eq 1 || $assemblySeq[4] eq 3 || $assemblySeq[4] eq 4 || $assemblySeq[4] eq 6 || $assemblySeq[4] eq 7 || $assemblySeq[4] eq 8) # add 5' 100 Ns
					{
						$assemblyCtgLength += $gapLength;
						$lastComponentType = 'U';
					}
				}
 			  	$assemblyCtgLength += $assemblySeqEnd - $assemblySeqStart + 1 - $filterLength;
				$lastComponentType = 'D';
				if($_ ne $lastAssemblySeq && $lastComponentType ne 'U')
				{
					if ($assemblySeq[4] eq 2 || $assemblySeq[4] eq 3 || $assemblySeq[4] eq 5 || $assemblySeq[4] eq 6 || $assemblySeq[4] eq 7 || $assemblySeq[4] eq 8) # add 5' 100 Ns
					{
						$assemblyCtgLength += $gapLength;				
						$lastComponentType = 'U';
					}
				}
			}
			if($renumber)
			{
				if($assemblyAllCtgList[4] > 0)
				{
					my $updateAssemblyCtgLength=$dbh->do("UPDATE matrix SET name = $assignedChrOrder, y = $assignedChrOrder, barcode = $assemblyCtgLength, note = '$assemblySeqList' WHERE id = $assemblyAllCtgList[0]");
					$assignedChrOrder++;
				}
				else
				{
					my $updateAssemblyCtgLength=$dbh->do("UPDATE matrix SET name = $totalCtgNumber, y = $totalCtgNumber, barcode = $assemblyCtgLength, note = '$assemblySeqList' WHERE id = $assemblyAllCtgList[0]");
					$totalCtgNumber--;
				}
			}
			else
			{
				my $updateAssemblyCtgLength=$dbh->do("UPDATE matrix SET y = $assignedChrOrder, barcode = $assemblyCtgLength, note = '$assemblySeqList' WHERE id = $assemblyAllCtgList[0]");
				$assignedChrOrder++;
			}
		}

		my $assemblyDetails = decode_json $assembly[8];
		$assemblyDetails->{'log'} = '' if (!exists $assemblyDetails->{'log'});
		$assemblyDetails->{'log'} .= "\n" if ($assemblyDetails->{'log'});
		#add log info
		$assemblyDetails->{'log'} .= "==== ". localtime() . " ====\n"
			."New Assembly: $replace;\n"
			."Physical Reference: $fpcOrAgpId;\n"
			."Reference Genome: $refGenomeId; Assign Chr: $assignChr; Orient Contigs: $orientContigs;\n"
			."Seq-to-Seq: $seqToSeq, Identity:$identitySeqToSeq, Overlap:$minOverlapSeqToSeq;\n"
			."Seq-to-Genome: $seqToGenome, Identity:$identitySeqToGenome, Overlap:$minOverlapSeqToGenome;\n"
			."End-to-End: $endToEnd, Identity:$identityEndToEnd, Overlap:$minOverlapEndToEnd;\n"
			."Filter Redundancy: Seq - $redundancyFilterSeq ($redundancySeq Hidden), Overlap - $redundancyFilterOverlap;\n"
			."Auto-Orient Seqs: $orientSeqs;\n"
			."Renumber Contigs: $renumber."
			;
		my $json = JSON->new->allow_nonref;
		$assemblyDetails = $json->encode($assemblyDetails);
		my $updateAssemblyToWork=$dbh->prepare("UPDATE matrix SET barcode = '1', note = ? WHERE id = ?");
		$updateAssemblyToWork->execute($assemblyDetails,$assemblyId);
	}
	else{
		die "couldn't fork: $!\n";
	} 
}
else
{
	print <<END;
<script>
	parent.errorPop("Please give an assembly id!");
</script>	
END
}
