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

undef $/;# enable slurp mode
my $html = <DATA>;

my $assemblyId = param ('assemblyId') || '';
my $assembly=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
$assembly->execute($assemblyId);
my @assembly = $assembly->fetchrow_array();
my $target=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
$target->execute($assembly[4]);
my @target = $target->fetchrow_array();

my $fpcOrAgpId = '';
my $doNotChangeFpc = ($assembly[7] != 0 && $assembly[6] > 0) ? '<sup class="ui-state-error ui-corner-all">Do NOT Change Unless You Plan To Re-Run Assembly!</sup><br>' : '';
if($target[1] eq "library")
{
	my $fpcList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'fpc' AND barcode = ?");
	$fpcList->execute($target[0]);
	while (my @fpcList = $fpcList->fetchrow_array())
	{
		$fpcOrAgpId .= ($fpcList[0] eq $assembly[6] ) ?
			"<option value='$fpcList[0]' title='$fpcList[8]' selected>FPC: $fpcList[2] v.$fpcList[3]</option>" :
			"<option value='$fpcList[0]' title='$fpcList[8]'>FPC: $fpcList[2] v.$fpcList[3]</option>";
	}
}
elsif($target[1] eq "genome")
{
	my $agpList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'agp' AND x = ?");
	$agpList->execute($target[0]);
	while (my @agpList = $agpList->fetchrow_array())
	{
		$fpcOrAgpId .= ($agpList[0] eq $assembly[6] ) ?
			"<option value='$agpList[0]' selected>AGP: $agpList[2] v.$agpList[3]</option>" :
			"<option value='$agpList[0]'>AGP: $agpList[2] v.$agpList[3]</option>";
	}
}
if($fpcOrAgpId)
{
	$fpcOrAgpId = "<option class='ui-state-error-text' value='0'>Please select a reference</option>".$fpcOrAgpId;
}
else
{
	$fpcOrAgpId = "<option class='ui-state-error-text' value='0'>No reference available</option>".$fpcOrAgpId;
}

my $doNotChangeGenome = ($assembly[7] != 0 && $assembly[5] > 0) ? '<sup class="ui-state-error ui-corner-all">Do NOT Change Unless You Plan To Re-Run Assembly!</sup><br>' : '';
my $refGenomeId = '';
my $genomeList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'genome'");
$genomeList->execute();
while (my @genomeList = $genomeList->fetchrow_array())
{
	next if ($genomeList[0] eq $assembly[4]);
	next if ($genomeList[5] < 1); #remove not for reference
	$refGenomeId .= ($genomeList[0] eq $assembly[5] ) ?
		"<option value='$genomeList[0]' title='$genomeList[8]' selected>$genomeList[2]</option>" :
		"<option value='$genomeList[0]' title='$genomeList[8]'>$genomeList[2]</option>";
}
if($refGenomeId)
{
	$refGenomeId = "<option class='ui-state-error-text' value='0'>Please select a genome</option>".$refGenomeId;
}
else
{
	$refGenomeId = "<option class='ui-state-error-text' value='0'>No reference genome available</option>".$refGenomeId;
}

$html =~ s/\$assemblyId/$assemblyId/g;
$html =~ s/\$assemblyName/$assembly[2]/g;
$html =~ s/\$assemblyVersion/$assembly[3]/g;
$html =~ s/\$doNotChangeFpc/$doNotChangeFpc/g;
$html =~ s/\$fpcOrAgpId/$fpcOrAgpId/g;
$html =~ s/\$doNotChangeGenome/$doNotChangeGenome/g;
$html =~ s/\$refGenomeId/$refGenomeId/g;
my $assemblyDetails = decode_json $assembly[8];
$assemblyDetails->{'description'} = '' if (!exists $assemblyDetails->{'description'});
$html =~ s/\$assemblyDescription/$assemblyDetails->{'description'}/g;
$assemblyDetails->{'autoCheckNewSeq'} = 0 if (!exists $assemblyDetails->{'autoCheckNewSeq'});
if($assemblyDetails->{'autoCheckNewSeq'})
{
	$html =~ s/\$autoCheck/ checked="checked"/g;
}
else
{
	$html =~ s/\$autoCheck//g;
}
$html =~ s/\$assemblyCreator/$assembly[9]/g;
$html =~ s/\$assemblyCreationDate/$assembly[10]/g;
print header;
print $html;

__DATA__
	<form id="editAssembly$assemblyId" name="editAssembly$assemblyId" action="assemblySave.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
	<input name="assemblyId" id="editAssemblyId" type="hidden" value="$assemblyId" />
	<table>
	<tr><td style='text-align:right'><label for="editAssemblyName"><b>Assembly Name</b></label></td><td><input class='ui-widget-content ui-corner-all' name="name" id="editAssemblyName" size="30" type="text" maxlength="32" value="$assemblyName"/><br>Version $assemblyVersion <sup class='ui-state-disabled'>by $assemblyCreator on $assemblyCreationDate</sup><br>
	<input type="checkbox" id="editAssemblyAutoCheckNewSeq" name="autoCheckNewSeq" value="1"$autoCheck><label for="editAssemblyAutoCheckNewSeq">AutoCheck New Sequences</label>
	</td></tr>
	<tr><td style='text-align:right'><label for='editAssemblyFpcOrAgp'><b>Physical Reference</b></label></td><td>$doNotChangeFpc<select class='ui-widget-content ui-corner-all' name='fpcOrAgpId' id='editAssemblyFpcOrAgp'>$fpcOrAgpId</select></td></tr>
	<tr><td style='text-align:right'><label for='editAssemblyRefGenome'><b>Reference Genome</b></label></td><td>$doNotChangeGenome<select class='ui-widget-content ui-corner-all' name='refGenomeId' id='editAssemblyRefGenome'>$refGenomeId</select></td></tr>
	<tr><td style='text-align:right'><label for="editAssemblyDescription"><b>Description</b></label></td><td><textarea class='ui-widget-content ui-corner-all' name="description" id="editAssemblyDescription" cols="50" rows="10" placeholder="Give some information about this assembly. Or you may do it later.">$assemblyDescription</textarea></td></tr>
	</table>
	</form>
<script>
$('#dialog').dialog("option", "title", "Edit Assembly");
$( "#dialog" ).dialog( "option", "buttons", [{ text: "Save", click: function() { submitForm('editAssembly$assemblyId'); } }, { text: "Delete", click: function() { deleteItem($assemblyId); } }, { text: "Cancel", click: function() {closeDialog(); } } ] );
</script>