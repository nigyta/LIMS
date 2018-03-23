#!/usr/bin/perl -w
use strict;
use CGI qw(:standard);
use CGI::Carp qw ( fatalsToBrowser ); 
use DBI;
use JSON::XS;
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
my $ctgListDetails;
my $commentDetails;
undef $/;# enable slurp mode
my $html = <DATA>;
if ($assemblyId)
{
	my $assemblyCtg = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? ORDER BY x,z,y");
	$assemblyCtg->execute($assemblyId);
	while (my @assemblyCtg = $assemblyCtg->fetchrow_array())
	{
		my @seq=split",",$assemblyCtg[8];
		my $num=@seq;
		my $commentDescription;
		my $comment = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'comment' AND o = ?");
		$comment->execute($assemblyCtg[0]);
		my @comment = $comment->fetchrow_array();
		if ($comment->rows > 0)
		{
			$commentDetails = decode_json $comment[8];
			$commentDetails->{'description'} = '' unless (exists $commentDetails->{'description'});
			$ctgListDetails.="<tr><td>Ctg$assemblyCtg[2]</td><td>$num</td><td>$assemblyCtg[4]</td><td>".commify($assemblyCtg[7])." </td><td>$commentDetails->{'description'}</td></tr>" ;
		}
		else
		{
			$ctgListDetails.="<tr><td>Ctg$assemblyCtg[2]</td><td>$num</td><td>$assemblyCtg[4]</td><td>".commify($assemblyCtg[7])." </td><td></td></tr>" ;
		}
	}
	
	$ctgListDetails = "
	<table id='ctgLengthDetails$$' class='display'><thead><tr><th><b>Contig</b></th><th><b>Number of assemblySeqs</b></th><th><b>Assigned chromosome #</b></th><th><b>Length (bp)</b></th><th><b>Comment</b></th></tr></thead><tbody>$ctgListDetails</tbody></table>
	";
	
}

$html =~ s/\$\$/$$/g;
$html =~ s/\$ctgListDetails/$ctgListDetails/g;
$html =~ s/\$assemblyId/$assemblyId/g;
$html =~ s/\$commoncfg->{HTDOCS}/$commoncfg->{HTDOCS}/g;
print header;
print $html;

__DATA__
<button style="float: right; margin-top: .3em; margin-right: .3em;" onclick="submitForm('assemblyCtg$assemblyId$$')">Download</button>
<button style="float: right; margin-top: .3em; margin-right: .3em;" onclick="printDiv('viewCtgLength$$')">Print</button>
<form id="assemblyCtg$assemblyId$$" name="assemblyCtg$assemblyId$$" action="download.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
<input name="assemblyIdForCtgList" id="assemblyIdForCtgList" type="hidden" value="$assemblyId" />
<div id="viewCtgLength$$" name="viewCtgLength$$">
$ctgListDetails
</div>
</form>
<script>
buttonInit();
$( "#ctgLengthDetails$$" ).dataTable({
	"dom": 'lfrtip',
	"scrollY": "500px",
	"scrollCollapse": true,
	"paging": false,
	"searching": false,
	"ordering": false,
	"info": false
});
</script>