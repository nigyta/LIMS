#!/usr/bin/perl -w
use strict;
use CGI qw(:standard);
use CGI::Carp qw ( fatalsToBrowser ); 
use JSON;
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

my $genebankId = "<option class='ui-state-error-text' value='0'>None</option>";
my $genebankList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'genebank' ORDER BY name");
$genebankList->execute();
while (my @genebankList = $genebankList->fetchrow_array())
{
	my $genebankDetails = decode_json $genebankList[8];
	$genebankDetails->{'comments'} = escapeHTML($genebankDetails->{'comments'});
	$genebankId .= "<option value='$genebankList[0]' title='$genebankDetails->{'comments'}'>Genebank: $genebankList[2]</option>";
}

$html =~ s/\$genebankId/$genebankId/g;

print header;
print $html;

__DATA__
<form id="newDart" name="newDart" action="dartSave.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
	<table>
	<tr><td style='text-align:right'><label for="newDartName"><b>DArT Name</b></label></td><td><input class='ui-widget-content ui-corner-all' name="name" id="newDartName" size="40" type="text" maxlength="32" /></td></tr>
	<tr><td style='text-align:right' rowspan='2'><label for="newDartFile"><b>DArT Report</b></label></td><td><input name="dartFile" id="newDartFile" type="file" />(in Tab Delimited Text format)</td></tr>
	<tr><td>or <input name="dartFilePath" id="newDartFilePath" type="text" />(On-server file name with full path)</td></tr>
	<tr><td style='text-align:right'><label for="newDartGenebankId"><b>Link to</b></label></td><td><select class='ui-widget-content ui-corner-all' name='genebankId' id='newDartGenebankId'>$genebankId</select></td></tr>
	<tr><td style='text-align:right'><label for="newDartDescription"><b>Description</b></label></td><td><textarea class='ui-widget-content ui-corner-all' name="description" id="newDartDescription" cols="50" rows="10"></textarea></td></tr>
	</table>
</form>
<script>
$('#dialog').dialog("option", "title", "New DArt Report");
$( "#dialog" ).dialog( "option", "buttons", [{ text: "Save", click: function() { submitForm('newDart'); } }, { text: "Cancel", click: function() {closeDialog(); } } ] );
</script>