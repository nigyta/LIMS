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
if ($fpcId)
{
	my $getFpcClones = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'fpcClone' AND o = ? ORDER BY name");
	$getFpcClones->execute($fpcId);
	if($getFpcClones->rows < 1)
	{
		print header(-type=>'text/html',-status=>'402 No valid download Id or Key Found');
	}
	else
	{
		print header(-type=>'text/plain',
		-attachment=>'fpcCloneList.txt',
		);
		while(my @getFpcClones= $getFpcClones->fetchrow_array())
		{
			print ">$getFpcClones[2]\n$getFpcClones[8]\n";
		}
	}
}
else
{
	print header(-type=>'text/html',-status=>'402 Invalid operation');
}