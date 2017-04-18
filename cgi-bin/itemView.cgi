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

my $itemId = param ('itemId') || '';
print header;
if ($itemId)
{
	my $item=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$item->execute($itemId);
	my @item = $item->fetchrow_array();
	my $itemDetails = decode_json $item[8];
	my $parent=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$parent->execute($item[6]);
	my @parent = $parent->fetchrow_array();	

	my $itemLine = '';
	for (sort {$a <=> $b} keys %$itemDetails)
	{
		$itemDetails->{$_}->{'field'} = '' unless ($itemDetails->{$_}->{'field'});
		$itemDetails->{$_}->{'value'} = '' unless ($itemDetails->{$_}->{'value'});
		$itemDetails->{$_}->{'value'} = escapeHTML($itemDetails->{$_}->{'value'});
		$itemDetails->{$_}->{'value'} =~ s/\n/<br>/g;
		if($itemDetails->{$_}->{'value'} =~ /\.(jpg|jpeg|png|tif|tiff)$/i)
		{
			$itemLine .= "<tr><td style='text-align:right;width:200px;'><b>$itemDetails->{$_}->{'field'}</b></td><td>";
			for (split "\;", $itemDetails->{$_}->{'value'})
			{
				$_ =~ s/^\s+|\s+$//g;
				$itemLine .= "<img src='$commoncfg->{HTDOCS}/data/images/$_'/>";
			}
			$itemLine .= "</td></tr>";
		}
		else
		{
			$itemLine .= ($itemDetails->{$_}->{'value'} =~ /:\/\//) ? "<tr><td style='text-align:right;width:200px;'><b>$itemDetails->{$_}->{'field'}</b></td>
							<td><a href='$itemDetails->{$_}->{'value'}' target='_blank'>$itemDetails->{$_}->{'value'}</a></td>
						</tr>" :
						"<tr><td style='text-align:right;width:200px;'><b>$itemDetails->{$_}->{'field'}</b></td>
							<td>$itemDetails->{$_}->{'value'}</td>
						</tr>";
		}
	}
	print <<END;
	<table>
	$itemLine
	</table>
	<script>
	\$('#dialog').dialog("option", "title", "View $item[1] $item[2] in $parent[1] $parent[2]");
	\$( "#dialog" ).dialog( "option", "buttons", [{ text: "Edit", click: function() { closeDialog();openDialog("itemEdit.cgi?itemId=$itemId"); } }, { text: "OK", click: function() {closeDialog(); } } ] );
	</script>
END
}
else
{
	print '402 Invalid operation';
	exit;
}
