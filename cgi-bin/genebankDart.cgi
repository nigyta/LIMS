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

my $dartId = param ('dartId') || '';
my $dart = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
$dart->execute($dartId);
my @dart=$dart->fetchrow_array();

my @headerRows = ("genotype name","Order number","DArT plate barcode","client plate barcode","well row position","well column position","sample comments");
my $genotypes = "
	<table id='dart$$' class='display'>
		<thead>
			<tr>";

foreach (@headerRows)
{
	$genotypes .= "<th><b>$_</b></th>";
}
	$genotypes .= "</tr>
		</thead>
		<tbody>";
my $getGenotypes = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'dartGenotype' AND z = ?");
$getGenotypes->execute($dartId);
while (my @getGenotypes = $getGenotypes->fetchrow_array())
{

	my $genotypeDetails = decode_json $getGenotypes[8];
	foreach (@headerRows)
	{
		$genotypeDetails->{$_} = '' unless (exists $genotypeDetails->{$_});
	}
	my $descriptionLength = length ($genotypeDetails->{$headerRows[6]});
	if ($descriptionLength > 35)
	{
		$genotypeDetails->{$headerRows[6]} = "<a title='$genotypeDetails->{$headerRows[6]}'>". substr($genotypeDetails->{$headerRows[6]},0,25). "...". substr($genotypeDetails->{$headerRows[6]},-5). "</a>";
	}

	$genotypes .= "<tr>";
	foreach (@headerRows)
	{
		$genotypes .= ($_ eq 'genotype name') ? "<td><a onclick='closeDialog();openDialog(\"genotypeView.cgi?genotypeId=$getGenotypes[0]\")'>$genotypeDetails->{$_}</a></td>" : "<td>$genotypeDetails->{$_}</td>";
	}
	$genotypes .= "</tr>";
}

$html =~ s/\$dartId/$dartId/g;
$html =~ s/\$dartName/$dart[2]/g;

$genotypes .= "</tbody></table>\n";

$html =~ s/\$snpNumber/$dart[3]/g;
$html =~ s/\$genotypeNumber/$dart[4]/g;
$dart[8] = escapeHTML($dart[8]);
$dart[8] =~ s/\n/<br>/g;
$html =~ s/\$dartDescription/$dart[8]/g;
$html =~ s/\$dartCreator/$dart[9]/g;
$html =~ s/\$dartCreationDate/$dart[10]/g;
$html =~ s/\$genotypes/$genotypes/g;
$html =~ s/\$\$/$$/g;
print header;
print $html;

__DATA__
<h3><a onclick='openDialog("dartView.cgi?dartId=$dartId")' title='View'>$dartName</a> <sub class='ui-state-disabled'>$snpNumber SNPs and $genotypeNumber genotypes</sub></h3>
<b>$dartDescription</b><br>
$genotypes
<script>
$( "#dart$$" ).dataTable({
	"scrollY": "400px",
	"scrollCollapse": true,
	"paging": false
});
</script>