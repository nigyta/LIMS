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

my $libraryId = param ('libraryId') || '';
if ($libraryId)
{
	my $poolClone;
	my $poolClones = $dbh->prepare("SELECT link.* FROM link,clones WHERE link.type LIKE 'poolClone' AND link.child = clones.name AND clones.libraryId = ? ORDER BY link.child");
	$poolClones->execute($libraryId);
	while(my @poolClones = $poolClones->fetchrow_array())
	{
		$poolClone->{$poolClones[1]} = $poolClones[0];
	}
	my $getClones = $dbh->prepare("SELECT * FROM clones WHERE libraryId = ?");
	$getClones->execute($libraryId);
	if($getClones->rows < 1)
	{
		print header(-type=>'text/html',-status=>'402 No valid download Id or Key Found');
	}
	else
	{
		print header(-type=>'text/plain',
		-attachment=>'cloneList.txt',
		);
		print "Clone\tOriginal\tSequence\n";
		while(my @getClones= $getClones->fetchrow_array())
		{
			if(exists $poolClone->{$getClones[1]})
			{
				print "$getClones[1]\t$getClones[5]\t$getClones[6]\tPooled\n";
			}
			else
			{
				print "$getClones[1]\t$getClones[5]\t$getClones[6]\n";
			}
		}
	}
}
else
{
	print header(-type=>'text/html',-status=>'402 Invalid operation');
}
