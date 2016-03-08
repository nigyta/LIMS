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

my $assemblyId = param ('assemblyId') || '';
my $seqOne = param ('seqOne') || '';
my $seqTwo = param ('seqTwo') || '';
my $autoSeqSearchUrl = 'autoSeqSearch.cgi';
if($assemblyId)
{
	$autoSeqSearchUrl .= "?assemblyId=$assemblyId";
}
$html =~ s/\$autoSeqSearchUrl/$autoSeqSearchUrl/g;
$html =~ s/\$assemblyId/$assemblyId/g;

if($seqOne)
{
	my $sequenceOne = $dbh->prepare("SELECT * FROM matrix WHERE id =  ?");
	$sequenceOne->execute($seqOne);
	my @sequenceOne = $sequenceOne->fetchrow_array();
	$html =~ s/\$seqOneLabel/$sequenceOne[2]/g;
	$html =~ s/\$seqOne/$seqOne/g;
}
else
{
	$html =~ s/\$seqOneLabel//g;
	$html =~ s/\$seqOne//g;
}

if($seqTwo)
{
	my $sequenceTwo = $dbh->prepare("SELECT * FROM matrix WHERE id =  ?");
	$sequenceTwo->execute($seqTwo);
	my @sequenceTwo = $sequenceTwo->fetchrow_array();
	$html =~ s/\$seqTwoLabel/$sequenceTwo[2]/g;
	$html =~ s/\$seqTwo/$seqTwo/g;
}
else
{
	$html =~ s/\$seqTwoLabel//g;
	$html =~ s/\$seqTwo//g;
}

print header;
print $html;

__DATA__
<form id="assemblyAlignCheck" name="assemblyAlignCheck" action="assemblyAlignCheck.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
	<input name="assemblyId" id="assemblyAlignCheckAssemblyId" type="hidden" value="$assemblyId" />
	<table>
	<tr>
		<td colspan="2"><label for="assemblyAlignCheckSeqOneLabel"><b>Sequence-1.</b></label><input name="seqOneLabel" id="assemblyAlignCheckSeqOneLabel" size="16" type="text" maxlength="16" VALUE="$seqOneLabel" placeholder="First Seq" onblur="checkBlank()" /><input class='ui-state-highlight ui-corner-all' name="seqOne" id="assemblyAlignCheckSeqOne" type="text" placeholder="First SeqId" title="First SeqId" VALUE="$seqOne" readonly="readonly"/><br>
		<label for="assemblyAlignCheckSeqTwoLabel"><b>Sequence-2.</b></label><input name="seqTwoLabel" id="assemblyAlignCheckSeqTwoLabel" size="16" type="text" maxlength="16" VALUE="$seqTwoLabel" placeholder="Second Seq" onblur="checkBlank()" /><input class='ui-state-highlight ui-corner-all' name="seqTwo" id="assemblyAlignCheckSeqTwo" type="text" placeholder="Second SeqId" title="Second SeqId" VALUE="$seqTwo" readonly="readonly" />
		</td>
	</tr>
	<tr>
		<td colspan="2"><input type="checkbox" id="assemblyAlignHiddenCheckbox" name="hidden" value="2"><label for="assemblyAlignHiddenCheckbox">Including Hidden Alignment (repetitive regions)</label></td>
	</tr>
	<tr>
		<td colspan="2"><input type="checkbox" id="assemblyAlignFilterCheckbox" name="filter" value="1" checked="checked"><label for="assemblyAlignFilterCheckbox">Filter Sequence with the same name</label></td>
	</tr>
	</table>
</form>
<script>
$('#dialog').dialog("option", "title", "Check Alignment");
$( "#dialog" ).dialog( "option", "buttons", [{ text: "Check", click: function() { loadingShow();submitForm('assemblyAlignCheck'); } }, { text: "Cancel", click: function() {closeDialog(); } } ] );
$( "#assemblyAlignCheckSeqOneLabel" ).autocomplete({
	source: "$autoSeqSearchUrl",
	minLength: 2,
	focus: function( event, ui ) {
    	$( "#assemblyAlignCheckSeqOne" ).val( ui.item.id );
    },
    select: function( event, ui ) {
    	$( "#assemblyAlignCheckSeqOne" ).val( ui.item.id );
    }
});
$( "#assemblyAlignCheckSeqTwoLabel" ).autocomplete({
	source: "$autoSeqSearchUrl",
	minLength: 2,
	focus: function( event, ui ) {
    	$( "#assemblyAlignCheckSeqTwo" ).val( ui.item.id );
    },
    select: function( event, ui ) {
    	$( "#assemblyAlignCheckSeqTwo" ).val( ui.item.id );
    }
});

function checkBlank(){
	if($( "#assemblyAlignCheckSeqOneLabel" ).val() == '')
	{
		$( "#assemblyAlignCheckSeqOne" ).val( '' );
	}
	if($( "#assemblyAlignCheckSeqTwoLabel" ).val() == '')
	{
		$( "#assemblyAlignCheckSeqTwo" ).val( '' );
	}
}
</script>