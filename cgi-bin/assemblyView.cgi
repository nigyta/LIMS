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
if($assembly[6])
{
	my $fpcOrAgpList=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$fpcOrAgpList->execute($assembly[6]);
	my @fpcOrAgpList = $fpcOrAgpList->fetchrow_array();
	if($fpcOrAgpList[1] eq 'fpc')
	{
		$fpcOrAgpId .= "<tr><td style='text-align:right'><b>Physical Reference</b></td><td title='$fpcOrAgpList[8]'>FPC: $fpcOrAgpList[2] v.$fpcOrAgpList[3]</td></tr>";
	}
	elsif($fpcOrAgpList[1]  eq 'agp')
	{
		$fpcOrAgpId .= "<tr><td style='text-align:right'><b>Physical Reference</b></td><td>AGP: $fpcOrAgpList[2] v.$fpcOrAgpList[3]</td></tr>";
	}
}

my $refGenomeId = '';
if($assembly[5])
{
	my $genomeList=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$genomeList->execute($assembly[5]);
	my @genomeList = $genomeList->fetchrow_array();
	$refGenomeId = "<tr><td style='text-align:right'><b>Reference Genome</b></td><td title='$genomeList[8]'>$genomeList[2]</td></tr>";
}

$html =~ s/\$assemblyId/$assemblyId/g;
$html =~ s/\$assemblyName/$assembly[2]/g;
$html =~ s/\$assemblyVersion/$assembly[3]/g;
$html =~ s/\$fpcOrAgpId/$fpcOrAgpId/g;
$html =~ s/\$refGenomeId/$refGenomeId/g;

my $assemblyDetails = decode_json $assembly[8];
$assemblyDetails->{'description'} = '' if (!exists $assemblyDetails->{'description'});
$html =~ s/\$assemblyDescription/$assemblyDetails->{'description'}/g;

$html =~ s/\$assemblyCreator/$assembly[9]/g;
$html =~ s/\$assemblyCreationDate/$assembly[10]/g;
print header;
print $html;

__DATA__
<table>
	<tr><td style='text-align:right'><b>Assembly Name</b></td><td>$assemblyName<br>Version $assemblyVersion <sup class='ui-state-disabled'>by $assemblyCreator on $assemblyCreationDate</sup></td></tr>
	$fpcOrAgpId
	$refGenomeId
	<tr><td style='text-align:right'><b>Description</b></td><td><textarea class='ui-widget-content ui-corner-all' name="description" id="viewAssemblyDescription" cols="50" rows="10" placeholder="Give some information about this assembly. Or you may do it later." readonly="readonly">$assemblyDescription</textarea></td></tr>
</table>
<script>
$('#dialog').dialog("option", "title", "View Assembly $assemblyName");
$( "#dialog" ).dialog( "option", "buttons", [{ text: "OK", click: function() {closeDialog(); } } ] );
</script>