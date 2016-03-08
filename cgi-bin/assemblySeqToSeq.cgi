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
my $userConfig = new userConfig;

my $assemblyId = param ('assemblyId') || '';
my $identitySeqToSeq = param ('identitySeqToSeq') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOSEQIDENTITY");
my $minOverlapSeqToSeq = param ('minOverlapSeqToSeq') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOSEQMINOVERLAP");
my $redoAllSeqToSeq = param ('redoAllSeqToSeq') || '0';
my $checkGood = param ('checkGood') || '0';
my $blastn = 'blast+/bin/blastn';
my $makeblastdb = 'blast+/bin/makeblastdb';

print header;

if($assemblyId)
{
	my $pid = fork();
	if ($pid) {
		print <<END;
<script>
	parent.closeDialog();
	parent.informationPop("It's running! This processing might take several minutes.");
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

		my $inAssemblySequenceId;
		my $assemblySeqs = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblySeq' AND o = ?");
		$assemblySeqs->execute($assemblyId);
		while(my @assemblySeqs = $assemblySeqs->fetchrow_array())
		{
			$inAssemblySequenceId->{$assemblySeqs[5]} = 1;
		}

		my $updateAssemblyToRunningSeqToSeq=$dbh->do("UPDATE matrix SET barcode = '-2' WHERE id = $assemblyId");

		my $assemblySequenceLength;
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
		open (BLAST,">/tmp/$assembly[4].$$.blastn") or die "can't open file: /tmp/$assembly[4].$$.blastn";
		if($redoAllSeqToSeq)
		{
			open (CMD,"$blastn -query /tmp/$assembly[4].$$.seq -db /tmp/$assembly[4].$$.seq -dust no -evalue 1e-200 -perc_identity $identitySeqToSeq -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
		}
		else
		{
			open (CMD,"$blastn -query /tmp/$assembly[4].$$.new.seq -db /tmp/$assembly[4].$$.seq -dust no -evalue 1e-200 -perc_identity $identitySeqToSeq -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
		}
		while(<CMD>)
		{
			/^#/ and next;
			print BLAST $_;
			my @hit = split("\t",$_);
			next if($hit[0] eq $hit[1]);
			next if($hit[3] < $minOverlapSeqToSeq);
			if($hit[6] == 1 || $hit[7] == $assemblySequenceLength->{$hit[0]})
			{
				$goodSequenceId->{$hit[0]}->{$hit[1]} = 1;
				$goodSequenceId->{$hit[1]}->{$hit[0]} = 1;
			}
		}
		close(CMD);
		close(BLAST);
		unlink("/tmp/$assembly[4].$$.seq");
		unlink("/tmp/$assembly[4].$$.new.seq");
		unlink("/tmp/$assembly[4].$$.seq.nhr");
		unlink("/tmp/$assembly[4].$$.seq.nin");
		unlink("/tmp/$assembly[4].$$.seq.nsq");
		unlink("/tmp/$assembly[4].$$.blastn");
		foreach my $queryId (keys %$goodSequenceId)
		{
			foreach my $subjectId (keys %{$goodSequenceId->{$queryId}})
			{
				my $deleteAlignmentA = $dbh->prepare("DELETE FROM alignment WHERE query = ? AND subject = ?");
				$deleteAlignmentA->execute($queryId,$subjectId);
				my $deleteAlignmentB = $dbh->prepare("DELETE FROM alignment WHERE query = ? AND subject = ?");
				$deleteAlignmentB->execute($subjectId,$queryId);

				my $getSequenceA = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
				$getSequenceA->execute($queryId);
				my @getSequenceA =  $getSequenceA->fetchrow_array();
				open (SEQA,">/tmp/$getSequenceA[0].$$.seq") or die "can't open file: /tmp/$getSequenceA[0].$$.seq";
				my $sequenceDetailsA = decode_json $getSequenceA[8];
				$sequenceDetailsA->{'id'} = '' unless (exists $sequenceDetailsA->{'id'});
				$sequenceDetailsA->{'description'} = '' unless (exists $sequenceDetailsA->{'description'});
				$sequenceDetailsA->{'sequence'} = '' unless (exists $sequenceDetailsA->{'sequence'});
				$sequenceDetailsA->{'gapList'} = '' unless (exists $sequenceDetailsA->{'gapList'});
				print SEQA ">$getSequenceA[0]\n$sequenceDetailsA->{'sequence'}\n";
				close(SEQA);

				my $getSequenceB = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
				$getSequenceB->execute($subjectId);
				my @getSequenceB =  $getSequenceB->fetchrow_array();
				open (SEQB,">/tmp/$getSequenceB[0].$$.seq") or die "can't open file: /tmp/$getSequenceB[0].$$.seq";
				my $sequenceDetailsB = decode_json $getSequenceB[8];
				$sequenceDetailsB->{'id'} = '' unless (exists $sequenceDetailsB->{'id'});
				$sequenceDetailsB->{'description'} = '' unless (exists $sequenceDetailsB->{'description'});
				$sequenceDetailsB->{'sequence'} = '' unless (exists $sequenceDetailsB->{'sequence'});
				$sequenceDetailsB->{'gapList'} = '' unless (exists $sequenceDetailsB->{'gapList'});
				print SEQB ">$getSequenceB[0]\n$sequenceDetailsB->{'sequence'}\n";
				close(SEQB);
				my @alignments;
				my $goodOverlap = ($checkGood) ? 0 : 1;
				open (CMD,"$blastn -query /tmp/$getSequenceA[0].$$.seq -subject /tmp/$getSequenceB[0].$$.seq -dust no -evalue 1e-200 -perc_identity $identitySeqToSeq -outfmt 6 |") or die "can't open CMD: $!";
				while(<CMD>)
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
				close(CMD);
				open (CMD,"$blastn -query /tmp/$getSequenceB[0].$$.seq -subject /tmp/$getSequenceA[0].$$.seq -dust no -evalue 1e-200 -perc_identity $identitySeqToSeq -outfmt 6 |") or die "can't open CMD: $!";
				while(<CMD>)
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
				close(CMD);						
				unlink("/tmp/$getSequenceA[0].$$.seq");
				unlink("/tmp/$getSequenceB[0].$$.seq");
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
	parent.errorPop("Please give an assembly id!");
</script>	
END
}