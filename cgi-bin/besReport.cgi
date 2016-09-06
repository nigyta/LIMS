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

my %seqDir = (
	0=>'NA',
	1=>'f',
	2=>'r'
	);

if(param ('libraryId'))
{
	my $libraryId = param ('libraryId');
	my $targetGenome;
	my @targetGenome;
	my $besToGenome;
	my $genomeList=$dbh->prepare("SELECT * FROM matrix WHERE z = ? AND container LIKE 'genome'");
	$genomeList->execute($libraryId);
	while (my @genomeList = $genomeList->fetchrow_array())
	{
		$targetGenome->{$genomeList[0]} = $genomeList[2];
		push @targetGenome,$genomeList[0];

		my $refSequence=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = ? ORDER BY y DESC");
		$refSequence->execute($genomeList[0]);
		while (my @refSequence = $refSequence->fetchrow_array())
		{
			my $refSequenceDetails = decode_json $refSequence[8];
			$refSequenceDetails->{'id'} = '' unless (exists $refSequenceDetails->{'id'});
			$refSequenceDetails->{'description'} = '' unless (exists $refSequenceDetails->{'description'});
			$refSequenceDetails->{'sequence'} = '' unless (exists $refSequenceDetails->{'sequence'});
			$refSequenceDetails->{'gapList'} = '' unless (exists $refSequenceDetails->{'gapList'});
			$refSequenceDetails->{'filter'} = '' unless (exists $refSequenceDetails->{'filter'});
			my $besLeftPosition;
			my $besRightPosition;
			my $besLeftDirection;
			my $besRightDirection;
			my $besLeftAlignment;
			my $besRightAlignment;
			my $besList=$dbh->prepare("SELECT * FROM alignment WHERE subject = ? AND program LIKE 'BES%' ORDER BY s_start");
			$besList->execute($refSequence[0]);
			while (my @besList = $besList->fetchrow_array())
			{
				my $besSequence=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
				$besSequence->execute($besList[2]);
				my @besSequence = $besSequence->fetchrow_array();
				if (exists $besLeftPosition->{$refSequence[0]}->{$besSequence[2]})
				{
					my $besDistance = $besList[10] - $besLeftPosition->{$refSequence[0]}->{$besSequence[2]};
					next if($besDistance > 300000 || $besDistance < 2000);
					next if($besLeftDirection->{$refSequence[0]}->{$besSequence[2]} == $besSequence[6]);
					$besRightDirection->{$refSequence[0]}->{$besSequence[2]} = $besSequence[6];
					$besRightPosition->{$refSequence[0]}->{$besSequence[2]} = ($besList[11] > $besList[10]) ? $besList[11] : $besList[10];
					$besRightAlignment->{$refSequence[0]}->{$besSequence[2]} = ($besList[11] > $besList[10]) ? "+" : "-";
					$besToGenome->{$genomeList[0]}->{$besSequence[2]} = "$refSequence[2] $besLeftPosition->{$refSequence[0]}->{$besSequence[2]} $besDistance $besLeftDirection->{$refSequence[0]}->{$besSequence[2]} $besSequence[6] $besLeftAlignment->{$refSequence[0]}->{$besSequence[2]} $besRightAlignment->{$refSequence[0]}->{$besSequence[2]}";
				}
				else
				{
					$besLeftPosition->{$refSequence[0]}->{$besSequence[2]} = ($besList[11] > $besList[10]) ? $besList[10] : $besList[11];
					$besLeftDirection->{$refSequence[0]}->{$besSequence[2]} = $besSequence[6];
					$besLeftAlignment->{$refSequence[0]}->{$besSequence[2]} = ($besList[11] > $besList[10]) ? "+" : "-";
				}
			}
		}
	}

	my $besClone;
	my $paredBes;
	my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 98 AND x = ? ORDER BY name,id");
	$getSequences->execute($libraryId);
	while(my @getSequences =  $getSequences->fetchrow_array())
	{
		my $sequenceDetails = decode_json $getSequences[8];
		$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
		$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
		$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
		$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
		$sequenceDetails->{'sequence'} =~ s/[^a-zA-Z0-9]//g;
		$sequenceDetails->{'sequence'} = multiLineSeq($sequenceDetails->{'sequence'},80);
		$besClone->{$getSequences[2]} .= "$seqDir{$getSequences[6]}:$getSequences[5] ";
		$paredBes->{$getSequences[2]} .= $seqDir{$getSequences[6]};
	}
	my $totalBes = $getSequences->rows; 
	my $besDetails = "<table id='bes$$' class='display' style='width: 100%;'>
			<thead>
				<tr>
					<th style='text-align:left'><b>Clone Name</b></th>
					<th style='text-align:left'><b>Direction:Length</b> (bp)</th>
					<th style='text-align:left'><b>BAC Hits</b></th>";
	for(@targetGenome)
	{
			$besDetails .= "<td><th style='text-align:left'><b>$targetGenome->{$_}</b></th></td>";
	}
	$besDetails = "</tr>
			</thead>
			<tbody>";
	my $paredBesNumber = 0;
	my $paredBesMapped;
	for (sort keys %$besClone)
	{
		my $besCloneName = $_;
		my $targetGenomeMatch = '';
		for(@targetGenome)
		{
				$targetGenomeMatch .= (exists $besToGenome->{$_}->{$besCloneName})? "<td>$besToGenome->{$_}->{$besCloneName}</td>" : "<td></td>";
				$paredBesMapped->{$_}++ if (exists $besToGenome->{$_}->{$besCloneName});
		}
		$besDetails .= "<tr><td>$besCloneName</td><td>$besClone->{$besCloneName}</td><td></td>$targetGenomeMatch</tr>";
		$paredBesNumber++ if ($paredBes->{$besCloneName} =~ /fr/);
	}	
	my $mappedPairs = '';
	$besDetails .= "<tr><td></td><td></td><td></td>"; 
	for(@targetGenome)
	{
			$besDetails .= "<td>$paredBesMapped->{$_}</td>";
			$mappedPairs .= ($mappedPairs) ? " and $paredBesMapped->{$_}($targetGenome->{$_})" : "$paredBesMapped->{$_}($targetGenome->{$_})";
	}
	$besDetails .= "</tr>"; 
	$besDetails .= "</tbody></table>"; 

	open (BESTEXT,">$commoncfg->{TMPDIR}/$libraryId.BES-report.html") or die "can't open file: $commoncfg->{TMPDIR}/$libraryId.BES-report.html";
	print BESTEXT $besDetails;
	close (BESTEXT);
	`gzip -f $commoncfg->{TMPDIR}/$libraryId.BES-report.html`;
	my $besReport = "<a href='$commoncfg->{TMPURL}/$libraryId.BES-report.html.gz' target='hiddenFrame'>Download Details</a>" if (-e "$commoncfg->{TMPDIR}/$libraryId.BES-report.html.gz");
	$html =~ s/\$besReport/$besReport/g;

	$html =~ s/\$totalBes/$totalBes/g;
	$html =~ s/\$paredBesNumber/$paredBesNumber/g;
	$html =~ s/\$mappedPairs/$mappedPairs/g;
	$html =~ s/\$\$/$$/g;
	print header;
	print $html;
}
else
{
	print header(-type=>'text/html',-status=>'402 Invalid operation');
}


__DATA__
<button style="float: right; margin-top: .3em; margin-right: .3em;" onclick="printDiv('besReport$$')">Print</button>
<div id="besReport$$"  name="besReport$$">
$totalBes BESs.<br>
$paredBesNumber pairs.<br>
$mappedPairs mapped pairs.<br>

$besReport
</div>
<script>
buttonInit();
$('#dialog').dialog("option", "title", "BES Report");
$( "#dialog" ).dialog( "option", "buttons", [ { text: "Print", click: function() {printDiv('besReport$$'); } }, { text: "OK", click: function() {closeDialog(); } } ] );
</script>