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
if(!$userId)
{
	print header;
	print <<eof;
	<h2>Error</h2>
	Please <a onclick="openDialog('login.cgi');">login</a> first!
	<script type="text/javascript">
		openDialog('login.cgi');
		loadingHide();
	</script>
eof
    exit;
}

my $commoncfg = readConfig("main.conf");
my $dbh=DBI->connect("DBI:mysql:$commoncfg->{DATABASE}:$commoncfg->{DBHOST}",$commoncfg->{USERNAME},$commoncfg->{PASSWORD});

undef $/;# enable slurp mode
my $html = <DATA>;
my $type = param ('type') || '';
my $parentId = param ('parentId') || '';
my $refresh = param ('refresh') || 'menu';

my $table = '';
my $allTable=$dbh->prepare("SELECT * FROM matrix WHERE container Like ? AND z = ?");
$allTable->execute($type,$parentId);
while (my @allTable = $allTable->fetchrow_array())
{
	$allTable[8] = escapeHTML($allTable[8]);
	$allTable[8] =~ s/\n/<br>/g;

	$table = "<form id='tableList$$' name='tableList$$'>
		<table id='table$$' class='display' style='width: 100%;'>
			<thead>
				<tr>
					<th style='text-align:left'><b>Name</b></th>
					<th style='text-align:left'><b>Creator</b></th>
					<th style='text-align:left'><b>Creation Date</b></th>
				</tr>
			</thead>
			<tbody>" unless($table);
	$table .= "<tr>
		<td title='Name'><a id='tableId$allTable[0]$$' onclick='openDialog(\"itemView.cgi?itemId=$allTable[0]\")' title='View'>$allTable[2]</a></td>
		<td title='Creator'>$allTable[9]</td>
		<td title='Creation date'>$allTable[10]</td>
		</tr>";
}
$table .= "</tbody></table></form>\n" if($table);
my $button = "<div class='ui-state-highlight ui-corner-all' style='padding: 0 .7em;'>
	<button style='float: right; margin-top: .3em; margin-right: .3em;' onclick='openDialogForm(\"itemDeleteForm.cgi\",\"tableList$parentId$$\")' title='Delete $type'>Delete $type</button>
	<button style='float: right; margin-top: .3em; margin-right: .3em;' onclick='openDialog(\"tableNew.cgi?type=$type&parentId=$parentId&refresh=$refresh\")'>New $type</button>
	<h3>$type list</h3>
	";

unless($table)
{
	$button .= "<p class='ui-state-error ui-corner-all' style='padding: .7em;'><span class='ui-icon ui-icon-alert' style='float: left; margin-right: .3em;'></span>
			<strong>No data available!</strong></p>";
}
$button .= "</div>\n";

$html =~ s/\$button/$button/g;
$html =~ s/\$table/$table/g;
$html =~ s/\$\$/$$/g;


print header();
print $html;

__DATA__
$button
$table
<style>
	.gridDartList { list-style-type: none; display:inline-block;margin: 0; padding: 0; width: 100%; }
	.gridDartList li { margin: 3px 3px 3px 0; padding: 1px; float: left; width: 100px; text-align: left; }
</style>
<script>
buttonInit();
$( "#table$$" ).dataTable({
	"scrollY": "600px",
	"scrollCollapse": true,
	"paging": false
});
loadingHide();
</script>