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

my $assemblySeqId = param ('assemblySeqId') || '';
my $scrollLeft = param ('scrollLeft') || '0';

my %seqType = (
	0=>'Assembled',
	1=>'BAC-Insert',
	2=>'BAC-Circularized',
	3=>'BAC-NonVector',
	4=>'BAC-Gapped',
	5=>'Partial',
	6=>'Vector/Mixer',
	7=>'Mixer',
	8=>'SHORT',
	98=>'BES',
	99=>'Genome'
	);

my %bacAssignType = (
	0=>'',
	1=>'TagValid',
	2=>'BesValid',
	3=>'TagValid+BesValid',
	4=>'TagForced'
	);

my %seqDir = (
	0=>'NA',
	1=>'f',
	2=>'r'
	);

if ($assemblySeqId)
{
	my $assemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$assemblySeq->execute($assemblySeqId);
	my @assemblySeq = $assemblySeq->fetchrow_array();

	my $assembly=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$assembly->execute($assemblySeq[3]);
	my @assembly = $assembly->fetchrow_array();

	my $target=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$target->execute($assembly[4]);
	my @target = $target->fetchrow_array();

	my $assemblySequence=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$assemblySequence->execute($assemblySeq[5]);
	my @assemblySequence = $assemblySequence->fetchrow_array();
	my $seqStart;
	my $seqEnd;
	if($assemblySeq[8])
	{
		($seqStart,$seqEnd) = split ",",$assemblySeq[8];
	}
	else
	{
		$seqStart = 1;
		$seqEnd = $assemblySeq[6];
		my $updateAssemblySeq=$dbh->do("UPDATE matrix SET note = '$seqStart,$seqEnd' WHERE id = $assemblySeq[0]");
	}
	my $sequenceIdSelector .= ($target[1] eq 'library') ? "<tr><td style='text-align:right'><input type='radio' id='maskAssemblySeqRadio$assemblySequence[0]' name='seqId' value='$assemblySequence[0]' checked='checked' onchange='setSeqLength($assemblySequence[5])'></td><td><label for='maskAssemblySeqRadio$assemblySequence[0]'>$seqType{$assemblySequence[3]} ($bacAssignType{$assemblySequence[7]}:$assemblySequence[6])</label> <a href='download.cgi?seqId=$assemblySequence[0]' title='Download this sequence' target='hiddenFrame'>" .commify($assemblySequence[5]). " bp</a> <sup><a onclick='closeDialog();openDialog(\"jobView.cgi?jobId=$assemblySequence[4]\")'>JobId: $assemblySequence[4]</a></sup></td></tr>"
		: "<tr><td style='text-align:right'><input type='radio' id='maskAssemblySeqRadio$assemblySequence[0]' name='seqId' value='$assemblySequence[0]' checked='checked' onchange='setSeqLength($assemblySequence[5])'></td><td><label for='maskAssemblySeqRadio$assemblySequence[0]'>$assemblySequence[2] (<a href='download.cgi?seqId=$assemblySequence[0]' title='Download this sequence' target='hiddenFrame'>" .commify($assemblySequence[5]). " bp</a>) in Genome <a onclick='closeDialog();openDialog(\"genomeView.cgi?genomeId=$assemblySequence[4]\")'>$target[2]</a></label></td></tr>";

	$html =~ s/\$scrollLeft/$scrollLeft/g;
	$html =~ s/\$assemblySeqId/$assemblySeqId/g;
	$html =~ s/\$assemblySeqName/$assemblySeq[2]/g;
	$html =~ s/\$seqLength/$assemblySeq[6]/g;
	$html =~ s/\$gapSize/$assemblySeq[4]/g;
	$html =~ s/\$seqStart/$seqStart/g;
	$html =~ s/\$seqEnd/$seqEnd/g;
	$html =~ s/\$sequenceIdSelector/$sequenceIdSelector/g;
	$html =~ s/\$\$/$$/g;
	print header;
	print $html;
}
else
{
	print header(-type=>'text/html',-status=>'402 Invalid operation');
	exit;
}


__DATA__
	<form id="maskAssemblySeq$assemblySeqId" name="maskAssemblySeq$assemblySeqId" action="assemblySeqMask.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
	<input name="assemblySeqId" id="maskAssemblySeqId$$" type="hidden" value="$assemblySeqId" />
	<input name="seqLength" id="maskAssemblySeqLength$$" type="hidden" value="$seqLength" />
	<input name="scrollLeft" id="maskAssemblyScrollLeft$$" type="hidden" value="$scrollLeft" />
	<table>
	<tr><td style='text-align:right;white-space: nowrap;'><b>Sequence</b></td>
	<td></td>
	</tr>
	$sequenceIdSelector
	<tr><td style='text-align:right;white-space: nowrap;'><b>Gap Size:</b></td>
	<td><input type="text" name="gapSize" id="gapSize$$" value="$gapSize" readonly="readonly"></td>
	</tr>
	<tr><td style='text-align:right;white-space: nowrap;'><b>Sequence Region:</b></td>
	<td><input type="text" name="seqStart" id="seqStart$$" value="$seqStart" onblur="changeSeqRegion();"> to <input type="text" name="seqEnd" id="seqEnd$$" value="$seqEnd" onblur="changeSeqRegion();"></td>
	</tr>
	<tr><td style='text-align:right'></td>
	<td><div id="slider-range$$"></div></td>
	</tr>
	<tr><td style='text-align:right'></td>
	<td>The selected region will be exported.</td>
	</tr>
	</table>
	</form>
<script>
$( "#slider-range$$" ).slider({
	  range: true,
	  min: 1,
	  max: $seqLength,
	  values: [ $seqStart, $seqEnd ],
	  slide: function( event, ui ) {
		$( "#seqStart$$" ).val( ui.values[ 0 ]);
		$( "#seqEnd$$" ).val( ui.values[ 1 ] );
	  }
});
$('#dialog').dialog("option", "title", "Set Sequence of $assemblySeqName");
$( "#dialog" ).dialog( "option", "buttons", [ { text: "Set", click: function() { submitForm('maskAssemblySeq$assemblySeqId'); } }, { text: "Cancel", click: function() {closeDialog();} } ] );
function changeSeqRegion()
{
	var seqStart = $( "#seqStart$$" ).val();
	var seqEnd = $( "#seqEnd$$" ).val();
	var max = $( "#slider-range$$" ).slider( "option", "max" );
	var min = $( "#slider-range$$" ).slider( "option", "min" );
	if(seqStart < min)
	{
		seqStart = min;
		$( "#seqStart$$" ).val(min);
	}	
	if(seqStart > max)
	{
		seqStart = max;
		$( "#seqStart$$" ).val(max);
	}	
	if(seqEnd < min)
	{
		seqEnd = min;
		$( "#seqEnd$$" ).val(min);
	}	
	if(seqEnd > max)
	{
		seqEnd = max;
		$( "#seqEnd$$" ).val(max);
	}	
	if (seqStart > seqEnd)
	{
		seqStart = seqEnd;
		$( "#seqStart$$" ).val(seqEnd);
	}
	$( "#slider-range$$" ).slider( "values", [seqStart, seqEnd]);
}
function setSeqLength(seqLength)
{
	$( "#slider-range$$" ).slider( "option", "max", seqLength );
	$( "#slider-range$$" ).slider( "values", [1, seqLength]);
	$( "#maskAssemblySeqLength$$" ).val(seqLength);
	$( "#seqStart$$" ).val(1);
	$( "#seqEnd$$" ).val(seqLength);
}
</script>