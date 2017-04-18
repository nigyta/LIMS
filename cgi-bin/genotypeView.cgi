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

my $genotypeId = param ('genotypeId') || '';
my @headerRows = ("genotype name","Order number","DArT plate barcode","client plate barcode","well row position","well column position","sample comments");

print header;
if ($genotypeId)
{
	my $genotypes = "";
	my $getGenotype = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$getGenotype->execute($genotypeId);
	if($getGenotype->rows < 1)
	{
		print 'No valid Genotype Found!';
		exit;
	}
	else
	{
		my @getGenotype = $getGenotype->fetchrow_array();
		my $genotypeDetails = decode_json $getGenotype[8];
		

		foreach (@headerRows)
		{
			$genotypeDetails->{$_} = '' unless (exists $genotypeDetails->{$_});
			$genotypes .= "<tr><td style='white-space: nowrap;'><b>$_</b></td><td>$genotypeDetails->{$_}</td></tr>";
		}

		my $getSNPs = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'dartSNP' AND z = ?");
		$getSNPs->execute($getGenotype[3]);
		while (my @getSNPs = $getSNPs->fetchrow_array())
		{
			my $snpDetails = decode_json $getSNPs[8];
			my $snpDetailsLine = '';
# 			for (keys %$snpDetails)
# 			{
# 				$snpDetailsLine .= "$_: $snpDetails->{$_}\n";
# 			}
			$genotypes .= "<tr><td style='white-space: nowrap;' title='$snpDetailsLine'><b>$getSNPs[2]</b></td><td>$genotypeDetails->{$getSNPs[0]}</td></tr>";
		}

		$html =~ s/\$\$/$$/g;
		$html =~ s/\$genotypeId/$genotypeId/g;		
		$html =~ s/\$genotypeName/$getGenotype[2]/g;
		$html =~ s/\$genotypes/$genotypes/g;
		$html =~ s/\$commoncfg->{HTDOCS}/$commoncfg->{HTDOCS}/g;

		print $html;
	}
}
else
{
	print 'No valid Genotype Found!';
	exit;
}

__DATA__
<div id="viewGenotype$$" name="viewGenotype$$">
	<table width='100%'>
	$genotypes
	</table>
</div>
<script>
buttonInit();
$('#dialog').dialog("option", "title", "View Genotype $genotypeName");
$( "#dialog" ).dialog( "option", "buttons", [ { text: "Print", click: function() {printDiv('viewGenotype$$'); } }, { text: "OK", click: function() {closeDialog(); } } ] );
</script>
