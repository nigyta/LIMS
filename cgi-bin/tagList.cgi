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
	my $getTags = $dbh->prepare("SELECT * FROM matrix WHERE x = ? AND container LIKE 'tag' ORDER BY o");
	$getTags->execute($libraryId);
	if($getTags->rows < 1)
	{
		print header(-type=>'text/html',-status=>'402 No valid download Id or Key Found');
	}
	else
	{
		print header(-type=>'text/plain',
		-attachment=>'tagList.tag',
		);
		my $lastTag='';
		while(my @getTags= $getTags->fetchrow_array())
		{
			if($lastTag eq $getTags[3])
			{
				print "$getTags[2],";
			}
			else
			{
				if($lastTag)
				{
					print "\n$getTags[8] $getTags[3] $getTags[2],";
				}
				else
				{
					print "$getTags[8] $getTags[3] $getTags[2],";
				}
			}
			$lastTag = $getTags[3];
		}
	}
}
else
{
	print header(-type=>'text/html',-status=>'402 Invalid operation');
}
