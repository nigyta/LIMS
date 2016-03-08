#!/usr/bin/perl -w
use strict;
use CGI qw(:standard);
use CGI::Carp qw ( fatalsToBrowser ); 
use DBI;
use lib "lib/";
use lib "lib/pangu";
use pangu;
use userConfig;
use userCookie;

my $userCookie = new userCookie;
my $userId = (cookie('cid')) ? $userCookie->checkCookie(cookie('cid')) : 0;
exit if (!$userId);

my $commoncfg = readConfig("main.conf");
my $dbh=DBI->connect("DBI:mysql:$commoncfg->{DATABASE}:$commoncfg->{DBHOST}",$commoncfg->{USERNAME},$commoncfg->{PASSWORD});
my $userConfig = new userConfig;
my $SEQTOSEQMINOVERLAP = $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOSEQMINOVERLAP");
my $SEQTOSEQIDENTITY = $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOSEQIDENTITY");

undef $/;# enable slurp mode
my $html = <DATA>;

my $assemblyId = param ('assemblyId') || '';
my $assembly=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
$assembly->execute($assemblyId);
my @assembly = $assembly->fetchrow_array();

$html =~ s/\$assemblyId/$assemblyId/g;
$html =~ s/\$assemblyName/$assembly[2]/g;
$html =~ s/\$SEQTOSEQMINOVERLAP/$SEQTOSEQMINOVERLAP/g;
$html =~ s/\$SEQTOSEQIDENTITY/$SEQTOSEQIDENTITY/g;

print header;
print $html;

__DATA__
<form id="newAssemblySeqToSeq" name="newAssemblySeqToSeq" action="assemblySeqToSeq.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
	<input name="assemblyId" id="newAssemblyId" type="hidden" value="$assemblyId" />
	<table>
	<tr><td><b>Alignment Settings:</b></td><td style='text-align:left' colspan='2'><input type="checkbox" id="newAssemblyRedoAllSeqToSeqCheckbox" name="redoAllSeqToSeq" value="1"><label for="newAssemblyRedoAllSeqToSeqCheckbox">For All Sequences</label></td><td><input type="checkbox" id="newAssemblySeqToSeqCheckGood" name="checkGood" value="1" checked="checked"><label for="newAssemblySeqToSeqCheckGood">Check End Match</label></td></tr>
	<tr><td></td><td style='text-align:right'><label for="newAssemblySeqToSeqMinOverlap"><b>Minimum Overlap</b></label><br>(length in bp)</td><td><input name="minOverlapSeqToSeq" id="newAssemblySeqToSeqMinOverlap" size="4" type="text" maxlength="6" VALUE="$SEQTOSEQMINOVERLAP" /></td></tr>
	<tr><td></td><td style='text-align:right'><label for="newAssemblySeqToSeqIdentity"><b>Minimum Identity</b></label><br>(%)</td><td><input name="identitySeqToSeq" id="newAssemblySeqToSeqIdentity" size="4" type="text" maxlength="4" VALUE="$SEQTOSEQIDENTITY" /></td></tr>
	</table>
</form>
<script>
$('#dialog').dialog("option", "title", "Run SEQ to SEQ Alignment ($assemblyName)");
$( "#dialog" ).dialog( "option", "buttons", [{ text: "Run Alignment", click: function() { submitForm('newAssemblySeqToSeq'); } }, { text: "Cancel", click: function() {closeDialog(); } } ] );
$( "#newAssemblySeqToSeqMinOverlap" ).spinner({
	min: 500,
	max: 99999,
	step: 100,
	start: function( event, ui ) {
		var current = $( "#newAssemblySeqToSeqMinOverlap" ).spinner( "value" );
		if(current >= 2000)
		{
			$( "#newAssemblySeqToSeqMinOverlap" ).spinner( "option", "step", 500 );
		}
		else
		{
			$( "#newAssemblySeqToSeqMinOverlap" ).spinner( "option", "step", 100 );
		}
	}
});
$( "#newAssemblySeqToSeqIdentity" ).spinner({ min: 90, max: 100});
</script>