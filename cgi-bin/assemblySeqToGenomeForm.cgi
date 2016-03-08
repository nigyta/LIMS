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
my $SEQTOGNMMINOVERLAP = $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOGNMMINOVERLAP");
my $SEQTOGNMIDENTITY = $userConfig->getFieldValueWithUserIdAndFieldName($userId,"SEQTOGNMIDENTITY");

undef $/;# enable slurp mode
my $html = <DATA>;

my $assemblyId = param ('assemblyId') || '';
my $assembly=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
$assembly->execute($assemblyId);
my @assembly = $assembly->fetchrow_array();

my $refGenomeId = '';
my $genomeList=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'genome'");
$genomeList->execute();
while (my @genomeList = $genomeList->fetchrow_array())
{
	next if ($genomeList[5] < 1); #remove not for reference
	$refGenomeId .= ($genomeList[0] eq $assembly[5] ) ?
		"<option value='$genomeList[0]' title='$genomeList[8]' selected>$genomeList[2]</option>" :
		"<option value='$genomeList[0]' title='$genomeList[8]'>$genomeList[2]</option>";
}
$html =~ s/\$assemblyId/$assemblyId/g;
$html =~ s/\$assemblyName/$assembly[2]/g;
$html =~ s/\$refGenomeId/$refGenomeId/g;
$html =~ s/\$SEQTOGNMMINOVERLAP/$SEQTOGNMMINOVERLAP/g;
$html =~ s/\$SEQTOGNMIDENTITY/$SEQTOGNMIDENTITY/g;

print header;
unless($refGenomeId)
{
	print <<END;
<script>
	closeDialog();
	errorPop("No genome available, please load one first!");
</script>	
END
}
print $html;

__DATA__
<form id="newAssemblySeqToGenome" name="newAssemblySeqToGenome" action="assemblySeqToGenome.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
	<input name="assemblyId" id="newAssemblyId" type="hidden" value="$assemblyId" />
	<table>
	<tr><td style='text-align:right'><label for="newAssemblySeqToGenome"><b>Reference Genome</b></label></td>
	<td colspan='2'><select class='ui-widget-content ui-corner-all' name="refGenomeId" id="newAssemblySeqToGenome">$refGenomeId</select></td>
	</tr>
	<tr><td><b>Alignment Settings:</b></td><td style='text-align:left' colspan='2'><input type="checkbox" id="newAssemblyRedoAllSeqToGenomeCheckbox" name="redoAllSeqToGenome" value="1"><label for="newAssemblyRedoAllSeqToGenomeCheckbox">For All Sequences</label><br>
		<input type="checkbox" id="newAssemblyMarkRepeatRegionCheckbox" name="markRepeatRegion" value="1" checked="checked"><label for="newAssemblyMarkRepeatRegionCheckbox">Mark Repeat Region</label>
		</td></tr>
	<tr><td></td><td style='text-align:right'><label for="newAssemblySeqToGenomeMinOverlap"><b>Minimum Overlap</b></label><br>(length in bp)</td><td><input name="minOverlapSeqToGenome" id="newAssemblySeqToGenomeMinOverlap" size="4" type="text" maxlength="6" VALUE="$SEQTOGNMMINOVERLAP" /></td></tr>
	<tr><td></td><td style='text-align:right'><label for="newAssemblySeqToGenomeIdentity"><b>Minimum Identity</b></label><br>(%)</td><td><input name="identitySeqToGenome" id="newAssemblySeqToGenomeIdentity" size="4" type="text" maxlength="4" VALUE="$SEQTOGNMIDENTITY" /></td></tr>
	</table>
</form>
<script>
$('#dialog').dialog("option", "title", "Run Seq to Genome Alignment ($assemblyName)");
$( "#dialog" ).dialog( "option", "buttons", [{ text: "Run Alignment", click: function() { submitForm('newAssemblySeqToGenome'); } }, { text: "Cancel", click: function() {closeDialog(); } } ] );
$( "#newAssemblySeqToGenomeMinOverlap" ).spinner({
	min: 500,
	max: 99999,
	step: 100,
	start: function( event, ui ) {
		var current = $( "#newAssemblySeqToGenomeMinOverlap" ).spinner( "value" );
		if(current >= 2000)
		{
			$( "#newAssemblySeqToGenomeMinOverlap" ).spinner( "option", "step", 500 );
		}
		else
		{
			$( "#newAssemblySeqToGenomeMinOverlap" ).spinner( "option", "step", 100 );
		}
	}
});
$( "#newAssemblySeqToGenomeIdentity" ).spinner({ min: 90, max: 100});
</script>