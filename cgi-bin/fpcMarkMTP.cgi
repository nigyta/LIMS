#!/usr/bin/perl -w
use strict;
use CGI qw(:standard);
use CGI::Carp qw ( fatalsToBrowser ); 
use DBI;
use lib "lib/";
use lib "lib/pangu";
use pangu;
use userCookie;

my $userCookie = new userCookie;
my $userId = (cookie('cid')) ? $userCookie->checkCookie(cookie('cid')) : 0;
exit if (!$userId);

my $commoncfg = readConfig("main.conf");
my $dbh=DBI->connect("DBI:mysql:$commoncfg->{DATABASE}:$commoncfg->{DBHOST}",$commoncfg->{USERNAME},$commoncfg->{PASSWORD});

my $fpcId = param ('fpcId') || '';
my $MTPClones = param('MTPClones') || '';
my $replace = param ('replace') || '0';
my @clones = split /\s+/, $MTPClones;

print header;
if ($fpcId)
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
		my $fpc=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$fpc->execute($fpcId);
		my @fpc = $fpc->fetchrow_array();
		my $library=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$library->execute($fpc[7]);
		my @library = $library->fetchrow_array();
		my $updateFpcCloneReplace=$dbh->do("UPDATE matrix SET y = 0 WHERE container LIKE 'fpcClone' AND o = $fpcId") if ($replace);	
		foreach my $bac (@clones)
		{
			$bac =~ s/[^a-zA-Z0-9]//g;
			$bac =~ /(\d+)(\D+)(\d+)$/;
			my $plateName =  sprintf "%0*d", 4, $1;
			my $row =  uc $2;
			my $col =  sprintf "%0*d", 2, $3;
			$bac = "$library[2]$plateName$row$col";
			my $updateFpcClone=$dbh->do("UPDATE matrix SET y = 1 WHERE container LIKE 'fpcClone' AND o = $fpcId AND name LIKE '$bac'");	
		}
	}
	else{
		die "couldn't fork: $!\n";
	} 
}
else
{
	print <<END;
<script>
	parent.errorPop("Not a valid operation!");
</script>	
END
}

