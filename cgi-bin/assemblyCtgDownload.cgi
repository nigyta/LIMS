#!/usr/bin/perl -w
use strict;
use CGI qw(:standard);
use CGI::Carp qw ( fatalsToBrowser ); 
use DBI;
use JSON;
use lib "lib/";
use lib "lib/pangu";
use pangu;
use user;
use userCookie;

my $userCookie = new userCookie;
my $userId = (cookie('cid')) ? $userCookie->checkCookie(cookie('cid')) : 0;
exit if (!$userId);

my $user = new user;
my $userDetail = $user->getAllFieldsWithUserId($userId);
my $userName = $userDetail->{"userName"};

my $commoncfg = readConfig("main.conf");
my $dbh=DBI->connect("DBI:mysql:$commoncfg->{DATABASE}:$commoncfg->{DBHOST}",$commoncfg->{USERNAME},$commoncfg->{PASSWORD});

my $assemblyId = param ('assemblyId') || '';

if ($assemblyId)
{
	print header(-type=>'application/octet-stream',
		-attachment=>"ctgLength.$assemblyId.len",
		);
	print "CTG\tSeq numbers\tLength(bp)\tComment\n";
	my $assemblyCtg = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? ORDER BY x,z,y");
	$assemblyCtg->execute($assemblyId);
	while (my @assemblyCtg = $assemblyCtg->fetchrow_array())
	{
		my @seq=split",",$assemblyCtg[8];
		my $num=@seq;
		my $commentDetails;
		my $comment = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'comment' AND o = ?");
		$comment->execute($assemblyCtg[0]);
		my @comment = $comment->fetchrow_array();
		if ($comment->rows > 0)
		{
			$commentDetails = decode_json $comment[8];
			$commentDetails->{'description'} = '' unless (exists $commentDetails->{'description'});
			$commentDetails->{'description'} =~ s/[\n\r]/\\n/g;
			print "Ctg$assemblyCtg[2]\t$num\t".commify($assemblyCtg[7])."\t'$commentDetails->{'description'}'\n";
		}
		else
		{
			print "Ctg$assemblyCtg[2]\t$num\t".commify($assemblyCtg[7])."\t\n";
		}
	}
}
else
{
	print header(-type=>'text/html',-status=>'402 Invalid operation');
	exit;
}
