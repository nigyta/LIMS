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

my $libraryId = param ('libraryId') || '';
my $targetId = param ('targetId') || '';

my $identityBesToSeq = param ('identityBesToSeq') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"BESTOSEQIDENTITY");
my $minOverlapBesToSeq = param ('minOverlapBesToSeq') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"BESTOSEQMINOVERLAP");
my $blastn = 'blast+/bin/blastn';
my $makeblastdb = 'blast+/bin/makeblastdb';

print header;

if($libraryId && $targetId)
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

		my $target=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$target->execute($targetId);
		my @target = $target->fetchrow_array();

		open (SEQALL,">/tmp/$targetId.$$.seq") or die "can't open file: /tmp/$targetId.$$.seq";
		if($target[1] eq 'library')
		{
			my $getClones = $dbh->prepare("SELECT * FROM clones WHERE sequenced > 0 AND libraryId = ?");
			$getClones->execute($targetId);
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
				}
			}
		}
		if($target[1] eq 'genome')
		{
			my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = ?");
			$getSequences->execute($targetId);
			while(my @getSequences = $getSequences->fetchrow_array())
			{
				my $sequenceDetails = decode_json $getSequences[8];
				$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
				$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
				$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
				$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
				print SEQALL ">$getSequences[0]\n$sequenceDetails->{'sequence'}\n";
			}
		}
		close(SEQALL);

		open (BES,">/tmp/$libraryId.$$.bes") or die "can't open file: /tmp/$libraryId.$$.bes";
		my $getBesSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 98 AND x = ?");
		$getBesSequences->execute($libraryId);
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

		open (BLAST,">/tmp/$libraryId.$$.blastn") or die "can't open file: /tmp/$libraryId.$$.blastn";
		system( "$makeblastdb -in /tmp/$targetId.$$.seq -dbtype nucl" );
		open (CMD,"$blastn -query /tmp/$libraryId.$$.bes -db /tmp/$targetId.$$.seq -dust no -evalue 1e-200 -perc_identity $identityBesToSeq -num_threads 8 -outfmt 6 |") or die "can't open CMD: $!";
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
		open (BLAST,"/tmp/$libraryId.$$.blastn") or die "can't open file: /tmp/$libraryId.$$.blastn";
		while(<BLAST>)
		{
			my @hit = split("\t",$_);
			#write to alignment
			my $insertAlignment=$dbh->prepare("INSERT INTO alignment VALUES ('', 'BEStoSEQ\_1e-200\_$identityBesToSeq\_$minOverlapBesToSeq', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)");
			$insertAlignment->execute(@hit);
		}
		close(BLAST);

		unlink("/tmp/$libraryId.$$.bes");
		unlink("/tmp/$targetId.$$.seq");
		unlink("/tmp/$targetId.$$.seq.nhr");
		unlink("/tmp/$targetId.$$.seq.nin");
		unlink("/tmp/$targetId.$$.seq.nsq");
		unlink("/tmp/$libraryId.$$.blastn");
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