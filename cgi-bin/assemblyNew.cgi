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

my $objectComponent;
$objectComponent->{0} = "Unknown";
$objectComponent->{1} = "Chr-Seq";
$objectComponent->{2} = "Ctg-Seq";

undef $/;# enable slurp mode
my $html = <DATA>;
my $targetId = param ('targetId') || '';
my $target=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
$target->execute($targetId);
my @target = $target->fetchrow_array();

my $fpcOrAgpId = '';
if($target[1] eq "library")
{
	my $fpcList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'fpc' AND barcode = ? ");
	$fpcList->execute($targetId);
	while (my @fpcList = $fpcList->fetchrow_array())
	{
		$fpcOrAgpId .= "<option value='$fpcList[0]' title='$fpcList[8]'>FPC: $fpcList[2] v.$fpcList[3]</option>";
	}
}
elsif($target[1] eq 'genome')
{
	my $agpList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'agp' AND x = ?");
	$agpList->execute($targetId);
	while (my @agpList = $agpList->fetchrow_array())
	{
		$fpcOrAgpId .= "<option value='$agpList[0]' title='$objectComponent->{$agpList[5]} AGP'>AGP: $agpList[2] v.$agpList[3]</option>";
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

my $refGenomeId = '';
my $genomeList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'genome'");
$genomeList->execute();
while (my @genomeList = $genomeList->fetchrow_array())
{
	next if ($genomeList[0] eq $targetId);
	next if ($genomeList[5] < 1); #remove not for reference
	$refGenomeId .= "<option value='$genomeList[0]' title='$genomeList[8]'>$genomeList[2]</option>";
}
if($refGenomeId)
{
	$refGenomeId = "<option class='ui-state-error-text' value='0'>Please select a genome</option>".$refGenomeId;
}
else
{
	$refGenomeId = "<option class='ui-state-error-text' value='0'>No reference genome available</option>".$refGenomeId;
}

$html =~ s/\$targetId/$targetId/g;
$html =~ s/\$assemblyName/$target[2]/g;
$html =~ s/\$fpcOrAgpId/$fpcOrAgpId/g;
$html =~ s/\$refGenomeId/$refGenomeId/g;

print header;
print $html;

__DATA__
	<form id="newAssembly$targetId" name="newAssembly$targetId" action="assemblySave.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
	<input name="targetId" id="targetId" type="hidden" value="$targetId" />
	<table>
	<tr><td style='text-align:right'><label for="newAssemblyName"><b>Assembly Name</b></label></td><td><input class='ui-widget-content ui-corner-all' name="name" id="newAssemblyName" size="40" type="text" maxlength="32" value="$assemblyName"/> <input type="checkbox" id="newAssemblyAutoCheckNewSeq" name="autoCheckNewSeq" value="1"><label for="newAssemblyAutoCheckNewSeq">AutoCheck New Sequences</label></td></tr>
	<tr><td style='text-align:right'><label for='newAssemblyFpcOrAgp'><b>Physical Reference</b></label></td><td><select class='ui-widget-content ui-corner-all' name='fpcOrAgpId' id='newAssemblyFpcOrAgp'>$fpcOrAgpId</select></td></tr>
	<tr><td style='text-align:right'><label for='newAssemblyRefGenome'><b>Reference Genome</b></label></td><td><select class='ui-widget-content ui-corner-all' name='refGenomeId' id='newAssemblyRefGenome'>$refGenomeId</select></td></tr>
	<tr><td style='text-align:right'><label for="newAssemblyDescription"><b>Description</b></label></td><td><textarea class='ui-widget-content ui-corner-all' name="description" id="newAssemblyDescription" cols="60" rows="10" placeholder="Give some information about this assembly. Or you may do it later."></textarea></td></tr>
	<tr><td></td><td><INPUT TYPE="button" VALUE="Save" onclick="submitForm('newAssembly$targetId');"></td></tr>
	</table>
	</form>
<script>
buttonInit();
loadingHide();
</script>