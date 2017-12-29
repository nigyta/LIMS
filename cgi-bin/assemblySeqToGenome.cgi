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
my $refGenomeId = param ('refGenomeId') || '';
my $identitySeqToGenome = param ('identitySeqToGenome') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOGNMIDENTITY");
my $minOverlapSeqToGenome = param ('minOverlapSeqToGenome') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOGNMMINOVERLAP");
my $alignEngine = param ('alignEngine') || 'blastn';
my $task = param ('megablast') || 'blastn';
my $softMasking = param ('softMasking') || '0';
my $redoAllSeqToGenome = param ('redoAllSeqToGenome') || '0';
my $markRepeatRegion = param ('markRepeatRegion') || '0';

print header;

if($assemblyId && $refGenomeId)
{
	my $pid = fork();
	if ($pid) {
		print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("It's running! This processing might take a while.");
</script>	
END
	}
	elsif($pid == 0){
		close (STDOUT);
		#connect to the mysql server
		my $dbh=DBI->connect("DBI:mysql:$commoncfg->{DATABASE}:$commoncfg->{DBHOST}",$commoncfg->{USERNAME},$commoncfg->{PASSWORD});
		my $assembly=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$assembly->execute($assemblyId);
		my @assembly = $assembly->fetchrow_array();

		my $target=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$target->execute($assembly[4]);
		my @target = $target->fetchrow_array();

		my $hasAlignmentSequenceId;
		my $updateAssemblyToRunningSeqToGenome=$dbh->do("UPDATE matrix SET barcode = '-4' WHERE id = $assemblyId");
		open (GENOME,">$commoncfg->{TMPDIR}/$refGenomeId.$$.genome") or die "can't open file: $commoncfg->{TMPDIR}/$refGenomeId.$$.genome";
		my $getGenome = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = ?");
		$getGenome->execute($refGenomeId);
		while(my @getGenome = $getGenome->fetchrow_array())
		{
			my $sequenceDetails = decode_json $getGenome[8];
			$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
			$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
			$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
			$sequenceDetails->{'sequence'} =~ tr/a-zA-Z/N/c; #replace nonword characters.;
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
				system( "$windowmasker -in $commoncfg->{TMPDIR}/$refGenomeId.$$.genome -infmt fasta -mk_counts -parse_seqids -out $commoncfg->{TMPDIR}/$refGenomeId.$$.genome_mask.counts" );
				system( "$windowmasker -in $commoncfg->{TMPDIR}/$refGenomeId.$$.genome -infmt fasta -ustat $commoncfg->{TMPDIR}/$refGenomeId.$$.genome_mask.counts -outfmt maskinfo_asn1_bin -parse_seqids -out $commoncfg->{TMPDIR}/$refGenomeId.$$.genome_mask.asnb" );
				system( "$makeblastdb -in $commoncfg->{TMPDIR}/$refGenomeId.$$.genome -inputtype fasta -dbtype nucl -parse_seqids -mask_data $commoncfg->{TMPDIR}/$refGenomeId.$$.genome_mask.asnb" );
			}
			else
			{
				system( "$makeblastdb -in $commoncfg->{TMPDIR}/$refGenomeId.$$.genome -dbtype nucl" );
			}
		}
		
		
		open (SEQALL,">$commoncfg->{TMPDIR}/$assembly[4].$$.seq") or die "can't open file: $commoncfg->{TMPDIR}/$assembly[4].$$.seq";
		open (SEQNEW,">$commoncfg->{TMPDIR}/$assembly[4].$$.new.seq") or die "can't open file: $commoncfg->{TMPDIR}/$assembly[4].$$.new.seq";
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
					$sequenceDetails->{'sequence'} =~ tr/a-zA-Z/N/c; #replace nonword characters.;
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
				$sequenceDetails->{'sequence'} =~ tr/a-zA-Z/N/c; #replace nonword characters.;
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
					open (CMD,"$alignEngineList->{$alignEngine} -query $commoncfg->{TMPDIR}/$assembly[4].$$.seq -task $task -db $commoncfg->{TMPDIR}/$refGenomeId.$$.genome -db_soft_mask 30 -evalue 1e-200 -perc_identity $identitySeqToGenome -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
				}
				else
				{
					open (CMD,"$alignEngineList->{$alignEngine} -query $commoncfg->{TMPDIR}/$assembly[4].$$.seq -task $task -db $commoncfg->{TMPDIR}/$refGenomeId.$$.genome -evalue 1e-200 -perc_identity $identitySeqToGenome -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
				}
			}
			else
			{
				open (CMD,"$alignEngineList->{$alignEngine} $commoncfg->{TMPDIR}/$refGenomeId.$$.genome $commoncfg->{TMPDIR}/$assembly[4].$$.seq -out=blast8 -minIdentity=$identitySeqToGenome |") or die "can't open CMD: $!";
			}
		
		}
		else
		{
			if($alignEngine eq 'blastn')
			{
				if($softMasking)
				{
					open (CMD,"$alignEngineList->{$alignEngine} -query $commoncfg->{TMPDIR}/$assembly[4].$$.new.seq -task $task -db $commoncfg->{TMPDIR}/$refGenomeId.$$.genome -db_soft_mask 30 -evalue 1e-200 -perc_identity $identitySeqToGenome -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
				}
				else
				{
					open (CMD,"$alignEngineList->{$alignEngine} -query $commoncfg->{TMPDIR}/$assembly[4].$$.new.seq -task $task -db $commoncfg->{TMPDIR}/$refGenomeId.$$.genome -evalue 1e-200 -perc_identity $identitySeqToGenome -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
				}
			}
			else
			{
				open (CMD,"$alignEngineList->{$alignEngine} $commoncfg->{TMPDIR}/$refGenomeId.$$.genome $commoncfg->{TMPDIR}/$assembly[4].$$.new.seq -out=blast8 -minIdentity=$identitySeqToGenome |") or die "can't open CMD: $!";
			}
			
	
		}
		while(<CMD>)
		{
			/^#/ and next;
			my @hit = split("\t",$_);
			next if($hit[3] < $minOverlapSeqToGenome);
			my $newSeqToGenome = "SEQ$hit[0]GNM$hit[1]";
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
		unlink("$commoncfg->{TMPDIR}/$assembly[4].$$.seq");
		unlink("$commoncfg->{TMPDIR}/$assembly[4].$$.new.seq");
		unlink("$commoncfg->{TMPDIR}/$refGenomeId.$$.genome");
		unlink("$commoncfg->{TMPDIR}/$refGenomeId.$$.genome.nhr");
		unlink("$commoncfg->{TMPDIR}/$refGenomeId.$$.genome.nin");
		unlink("$commoncfg->{TMPDIR}/$refGenomeId.$$.genome.nsq");
		`rm $commoncfg->{TMPDIR}/*.aln.html`; #delete cached files
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
				my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE program = 'SEQtoGNM\_$refGenomeId\_1e-200\_$identitySeqToGenome\_$minOverlapSeqToGenome' AND align_length < 5000 AND hidden = 0 ORDER BY query,q_start,q_end");
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
		my $updateAssemblyToWork=$dbh->do("UPDATE matrix SET barcode = '1' WHERE id = $assemblyId");
	}
	else{
		die "couldn't fork: $!\n";
	} 
}
else
{
	print <<END;
<script>
	parent.errorPop("Please give an assembly and genome id!");
</script>	
END
}