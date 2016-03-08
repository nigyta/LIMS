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

undef $/;# enable slurp mode
my $html = <DATA>;

my $fpcId = param ('fpcId') || '';
if ($fpcId)
{
	my $fpc=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$fpc->execute($fpcId);
	my @fpc = $fpc->fetchrow_array();
	$html =~ s/\$fpcId/$fpcId/g;
	$html =~ s/\$fpcName/$fpc[2]/g;
	$html =~ s/\$fpcVersion/$fpc[3]/g;
}
else
{
	print header(-type=>'text/html',-status=>'402 Invalid operation');
	print <<END;
<script>
	errorPop("Not a valid operation!");
</script>	
END
	exit;
}


print header;
print $html;

__DATA__
<form id="markMTP" name="markMTP" action="fpcMarkMTP.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
<h3>Mark MTP clones in '$fpcName v.$fpcVersion':</h3>
	<input name="fpcId" id="fpcId" type="hidden" value="$fpcId" />
	<table>
	<tr><td style='text-align:right'><label for="markMTPClones"><b>MTP Clones</b></label><br><sub id="markMTPClones_count" style="display:none"></sub></td><td><textarea class='ui-widget-content ui-corner-all word_count' name="MTPClones" id="markMTPClones" cols="50" rows="8"></textarea></td></tr>
	<tr><td style='text-align:left' colspan='2'><label for="markMTPCloneReplace">Are you going to clear all marked MTP clones before marking the above clones?</label></td></tr>
	<tr><td style='text-align:right'></td>
		<td>
		<div id="markMTPCloneReplace">
			<input type="radio" id="markMTPCloneReplaceRadio2" name="replace" value="1"><label for="markMTPCloneReplaceRadio2">Yes</label>
			<input type="radio" id="markMTPCloneReplaceRadio1" name="replace" value="0" checked="checked"><label for="markMTPCloneReplaceRadio1">No</label>
		</div>
	</td></tr>
	</table>
</form>
<script>
$('#dialog').dialog("option", "title", "Mark MTP Clones");
$( "#dialog" ).dialog( "option", "buttons", [{ text: "Submit", click: function() { submitForm('markMTP'); } }, { text: "Cancel", click: function() {closeDialog(); } } ] );
$( "#markMTPCloneReplace" ).buttonset();
wordCount('clone');
</script>
