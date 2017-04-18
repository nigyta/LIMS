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

my $parentId = "<option class='ui-state-error-text' value='0'>None</option>";
my $parentList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'genebank' ORDER BY name");
$parentList->execute();
while (my @parentList = $parentList->fetchrow_array())
{
	$parentId .= "<option value='$parentList[0]' title='$parentList[2]}'>$parentList[1]: $parentList[2]</option>";
}

$html =~ s/\$parentId/$parentId/g;

print header;
print $html;

__DATA__
<form id="newDataset" name="newDataset" action="datasetSave.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
	<table>
	<tr><td style='text-align:right'><label for="newDatasetName"><b>Dataset Name</b></label></td><td><input class='ui-widget-content ui-corner-all' name="name" id="newDatasetName" size="40" type="text" maxlength="32" /></td></tr>
	<tr><td style='text-align:right' rowspan='2'><label for="newDatasetFile"><b>File</b></label></td><td><input name="datasetFile" id="newDatasetFile" type="file" />(in Tab Delimited Text format)</td></tr>
	<tr><td>or <input name="datasetFilePath" id="newDatasetFilePath" type="text" />(On-server file name with full path)</td></tr>
	<tr><td><label for="newDatasetIdColumn">Column for Name </label></td><td><input type="text" id="newDatasetIdColumn" name="idColumn" value="1"></td></tr>
	<tr><td style='text-align:right'><label for="newDatasetParentId"><b>Link to</b></label></td><td><select class='ui-widget-content ui-corner-all' name='parentId' id='newDatasetParentId'>$parentId</select></td></tr>
	<tr><td style='text-align:right'><label for="newDatasetDescription"><b>Description</b></label></td><td><textarea class='ui-widget-content ui-corner-all' name="description" id="newDatasetDescription" cols="50" rows="10"></textarea></td></tr>
	</table>
</form>
<script>
$('#dialog').dialog("option", "title", "New Dataset");
$( "#dialog" ).dialog( "option", "buttons", [{ text: "Save", click: function() { submitForm('newDataset'); } }, { text: "Cancel", click: function() {closeDialog(); } } ] );
</script>