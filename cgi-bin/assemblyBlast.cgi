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

my $identityBlast = param ('identityBlast') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOSEQIDENTITY");
my $minOverlapBlast = param ('minOverlapBlast') || $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOSEQMINOVERLAP");

my $checkGood = param ('checkGood') || '0';
my $seqOne = param ('seqOne') || '';
my $seqTwo = param ('seqTwo') || '';
my $redo = param ('redo') || '0';
my $assemblyId = param ('assemblyId') || '';
my $assemblyAlignCheckFormUrl = "assemblyAlignCheckForm.cgi";
if($assemblyId)
{
	$assemblyAlignCheckFormUrl .= "?assemblyId=$assemblyId";
}
my $blastn = 'blast+/bin/blastn';

print header;

if($seqOne && $seqTwo)
{
	if($seqOne == $seqTwo)
	{
		print <<END;
<script>
	parent.errorPop("Please input two different sequences!");
</script>
END
		exit;
	}
	my $pid = fork();
	if ($pid) {
		print <<END;
<script>
	parent.closeDialog();
	parent.informationPop("It's running! This processing might take several minutes.");
	parent.openDialog('$assemblyAlignCheckFormUrl&seqOne=$seqOne&seqTwo=$seqTwo');
</script>	
END
	}
	elsif($pid == 0){
		close (STDOUT);
		#connect to the mysql server
		my $dbh=DBI->connect("DBI:mysql:$commoncfg->{DATABASE}:$commoncfg->{DBHOST}",$commoncfg->{USERNAME},$commoncfg->{PASSWORD});
		exit if ($seqOne == $seqTwo);

		my $getSequenceA = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$getSequenceA->execute($seqOne);
		my @getSequenceA = $getSequenceA->fetchrow_array();
		open (SEQA,">/tmp/$getSequenceA[0].$$.seq") or die "can't open file: /tmp/$getSequenceA[0].$$.seq";
		my $sequenceDetailsA = decode_json $getSequenceA[8];
		$sequenceDetailsA->{'id'} = '' unless (exists $sequenceDetailsA->{'id'});
		$sequenceDetailsA->{'description'} = '' unless (exists $sequenceDetailsA->{'description'});
		$sequenceDetailsA->{'sequence'} = '' unless (exists $sequenceDetailsA->{'sequence'});
		$sequenceDetailsA->{'gapList'} = '' unless (exists $sequenceDetailsA->{'gapList'});
		print SEQA ">$getSequenceA[0]\n$sequenceDetailsA->{'sequence'}\n";
		close(SEQA);
		my $getSequenceB = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$getSequenceB->execute($seqTwo);
		my @getSequenceB =  $getSequenceB->fetchrow_array();
		open (SEQB,">/tmp/$getSequenceB[0].$$.seq") or die "can't open file: /tmp/$getSequenceB[0].$$.seq";
		my $sequenceDetailsB = decode_json $getSequenceB[8];
		$sequenceDetailsB->{'id'} = '' unless (exists $sequenceDetailsB->{'id'});
		$sequenceDetailsB->{'description'} = '' unless (exists $sequenceDetailsB->{'description'});
		$sequenceDetailsB->{'sequence'} = '' unless (exists $sequenceDetailsB->{'sequence'});
		$sequenceDetailsB->{'gapList'} = '' unless (exists $sequenceDetailsB->{'gapList'});
		print SEQB ">$getSequenceB[0]\n$sequenceDetailsB->{'sequence'}\n";
		close(SEQB);
		if($redo)
		{
			my $deleteAlignmentA = $dbh->prepare("DELETE FROM alignment WHERE query = ? AND subject = ?");
			$deleteAlignmentA->execute($getSequenceA[0],$getSequenceB[0]);
			my $deleteAlignmentB = $dbh->prepare("DELETE FROM alignment WHERE query = ? AND subject = ?");
			$deleteAlignmentB->execute($getSequenceB[0],$getSequenceA[0]);
		}
		my $getAlignment = $dbh->prepare("SELECT * FROM alignment WHERE query = ? AND subject = ?");
		$getAlignment->execute($getSequenceA[0],$getSequenceB[0]);
		if($getAlignment->rows > 0)
		{
			next;
		}
		else
		{
			my @alignments;
			my $goodOverlap = ($checkGood) ? 0 : 1;
			open (CMD,"$blastn -query /tmp/$getSequenceA[0].$$.seq -subject /tmp/$getSequenceB[0].$$.seq -dust no -evalue 1e-200 -perc_identity $identityBlast -outfmt 6 |") or die "can't open CMD: $!";
			while(<CMD>)
			{
				/^#/ and next;
				my @hit = split("\t",$_);
				if($hit[3] >= $minOverlapBlast)
				{
					push @alignments, $_;
					if($hit[6] == 1 || $hit[7] == $getSequenceA[5])
					{
						$goodOverlap = 1;
					}
				}									
			}
			close(CMD);
			open (CMD,"$blastn -query /tmp/$getSequenceB[0].$$.seq -subject /tmp/$getSequenceA[0].$$.seq -dust no -evalue 1e-200 -perc_identity $identityBlast -outfmt 6 |") or die "can't open CMD: $!";
			while(<CMD>)
			{
				/^#/ and next;
				my @hit = split("\t",$_);
				if($hit[3] >= $minOverlapBlast)
				{
					push @alignments, $_;
					if($hit[6] == 1 || $hit[7] == $getSequenceB[5])
					{
						$goodOverlap = 1;
					}
				}									
			}
			close(CMD);						
			if($goodOverlap)
			{
				foreach (@alignments)
				{
					my @hit = split("\t",$_);
					#write to alignment
					my $insertAlignment=$dbh->prepare("INSERT INTO alignment VALUES ('', 'SEQtoSEQ_1e-200_$identityBlast\_$minOverlapBlast', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)");
					$insertAlignment->execute(@hit);
				}
			}
		}
		unlink("/tmp/$getSequenceB[0].$$.seq");
		unlink("/tmp/$getSequenceA[0].$$.seq");
	}
	else{
		die "couldn't fork: $!\n";
	} 
}
else
{
	print <<END;
<script>
	parent.errorPop("Please give two seqeunce names!");
</script>	
END
}