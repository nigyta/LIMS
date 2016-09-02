#!/usr/bin/perl -w
use strict;
use CGI qw(:standard);
use CGI::Carp qw ( fatalsToBrowser ); 
use JSON; #JSON::XS is recommended to be installed for handling JSON string of big size 
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
my %seqDir = (
	0=>'NA',
	1=>'f',
	2=>'r'
	);

if(param ('libraryId'))
{
	my $libraryId = param ('libraryId');
	print header;
	my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 98 AND x = ? ORDER BY name,id");
	$getSequences->execute($libraryId);
	while(my @getSequences =  $getSequences->fetchrow_array())
	{
		my $sequenceDetails = decode_json $getSequences[8];
		$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
		$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
		$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
		$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
		$sequenceDetails->{'sequence'} =~ s/[^a-zA-Z0-9]//g;
		$sequenceDetails->{'sequence'} = multiLineSeq($sequenceDetails->{'sequence'},80);
		print ">$getSequences[2].$seqDir{$getSequences[6]} ID-$getSequences[0] $getSequences[5] bp $sequenceDetails->{'description'}\n";
	}		
}
else
{
	print header(-type=>'text/html',-status=>'402 Invalid operation');
}
