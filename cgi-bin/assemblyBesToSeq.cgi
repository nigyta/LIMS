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
my $identityBesToSeq = param ('identityBesToSeq') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"BESTOSEQIDENTITY");
my $minOverlapBesToSeq = param ('minOverlapBesToSeq') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"BESTOSEQMINOVERLAP");
my $redoAllBesToSeq = param ('redoAllBesToSeq') || '0';
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

		my $updateAssemblyToRunningBesToSeq=$dbh->do("UPDATE matrix SET barcode = '-12' WHERE id = $assemblyId");
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

		open (BES,">/tmp/$assembly[4].$$.bes") or die "can't open file: /tmp/$assembly[4].$$.bes";
		my $getBesSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 98 AND x = ?");
		$getBesSequences->execute($assembly[4]);
		while(my @getBesSequences = $getBesSequences->fetchrow_array())
		{
			my $sequenceDetails = decode_json $getBesSequences[8];
			$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
			$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
			$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
			$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
			print BES ">$getBesSequences[0]\n$sequenceDetails->{'sequence'}\n";
		}
		close(BES);

		open (BLAST,">/tmp/$assembly[4].$$.blastn") or die "can't open file: /tmp/$assembly[4].$$.blastn";
		if($redoAllBesToSeq)
		{
			system( "$makeblastdb -in /tmp/$assembly[4].$$.seq -dbtype nucl" );
			open (CMD,"$blastn -query /tmp/$assembly[4].$$.bes -db /tmp/$assembly[4].$$.seq -dust no -evalue 1e-200 -perc_identity $identityBesToSeq -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
		}
		else
		{
			system( "$makeblastdb -in /tmp/$assembly[4].$$.new.seq -dbtype nucl" );
			open (CMD,"$blastn -query /tmp/$assembly[4].$$.bes -db /tmp/$assembly[4].$$.new.seq -dust no -evalue 1e-200 -perc_identity $identityBesToSeq -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
		}
		while(<CMD>)
		{
			/^#/ and next;
			my @hit = split("\t",$_);
			next if($hit[3] < $minOverlapBesToSeq);
			my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE query = ? AND subject = ?");
			$getAlignment->execute($hit[0],$hit[1]);
			if($getAlignment->rows > 0)
			{
				next;
			}
			else
			{
				print BLAST $_;
			}
		}
		close(CMD);
		close(BLAST);
		open (BLAST,"/tmp/$assembly[4].$$.blastn") or die "can't open file: /tmp/$assembly[4].$$.blastn";
		while(<BLAST>)
		{
			my @hit = split("\t",$_);
			#write to alignment
			my $insertAlignment=$dbh->prepare("INSERT INTO alignment VALUES ('', 'BEStoBAC\_1e-200\_$identityBesToSeq\_$minOverlapBesToSeq', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)");
			$insertAlignment->execute(@hit);
		}
		close(BLAST);

		if($redoAllBesToSeq)
		{
			unlink("/tmp/$assembly[4].$$.bes");
			unlink("/tmp/$assembly[4].$$.seq");
			unlink("/tmp/$assembly[4].$$.new.seq");
			unlink("/tmp/$assembly[4].$$.seq.nhr");
			unlink("/tmp/$assembly[4].$$.seq.nin");
			unlink("/tmp/$assembly[4].$$.seq.nsq");
			unlink("/tmp/$assembly[4].$$.blastn");
		}
		else
		{
			unlink("/tmp/$assembly[4].$$.bes");
			unlink("/tmp/$assembly[4].$$.seq");
			unlink("/tmp/$assembly[4].$$.new.seq");
			unlink("/tmp/$assembly[4].$$.new.seq.nhr");
			unlink("/tmp/$assembly[4].$$.new.seq.nin");
			unlink("/tmp/$assembly[4].$$.new.seq.nsq");
			unlink("/tmp/$assembly[4].$$.blastn");
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