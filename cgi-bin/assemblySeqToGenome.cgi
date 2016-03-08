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

my $assemblyId = param ('assemblyId') || '';
my $refGenomeId = param ('refGenomeId') || '';
my $identitySeqToGenome = param ('identitySeqToGenome') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOGNMIDENTITY");
my $minOverlapSeqToGenome = param ('minOverlapSeqToGenome') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOGNMMINOVERLAP");
my $redoAllSeqToGenome = param ('redoAllSeqToGenome') || '0';
my $markRepeatRegion = param ('markRepeatRegion') || '0';
my $blastn = 'blast+/bin/blastn';
my $makeblastdb = 'blast+/bin/makeblastdb';

print header;

if($assemblyId && $refGenomeId)
{
	my $pid = fork();
	if ($pid) {
		print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("It's running! This processing might take several minutes.");
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

		my $updateAssemblyToRunningSeqToGenome=$dbh->do("UPDATE matrix SET barcode = '-4' WHERE id = $assemblyId");
		open (GENOME,">/tmp/$refGenomeId.$$.genome") or die "can't open file: /tmp/$refGenomeId.$$.genome";
		my $getGenome = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = ?");
		$getGenome->execute($refGenomeId);
		while(my @getGenome = $getGenome->fetchrow_array())
		{
			my $sequenceDetails = decode_json $getGenome[8];
			$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
			$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
			$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
			$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
			print GENOME ">$getGenome[0]\n$sequenceDetails->{'sequence'}\n";
		}
		close(GENOME);
		system( "$makeblastdb -in /tmp/$refGenomeId.$$.genome -dbtype nucl" );

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
		my $newSeqToGenomeFound;
		if($redoAllSeqToGenome)
		{
			open (CMD,"$blastn -query /tmp/$assembly[4].$$.seq -db /tmp/$refGenomeId.$$.genome -dust no -evalue 1e-200 -perc_identity $identitySeqToGenome -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
		}
		else
		{
			open (CMD,"$blastn -query /tmp/$assembly[4].$$.new.seq -db /tmp/$refGenomeId.$$.genome -dust no -evalue 1e-200 -perc_identity $identitySeqToGenome -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
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
		unlink("/tmp/$refGenomeId.$$.genome");
		unlink("/tmp/$refGenomeId.$$.genome.nhr");
		unlink("/tmp/$refGenomeId.$$.genome.nin");
		unlink("/tmp/$refGenomeId.$$.genome.nsq");
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