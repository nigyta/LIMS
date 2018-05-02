#!/usr/bin/perl -w
use strict;
use CGI qw(:standard);
use CGI::Carp qw ( fatalsToBrowser ); 
use DBI;
use JSON::XS;
use lib "lib/";
use lib "lib/pangu";
use pangu;
use user;
use userCookie;

my $userCookie = new userCookie;
my $userId = (cookie('cid')) ? $userCookie->checkCookie(cookie('cid')) : 0;
exit if (!$userId);

my $user = new user;
my $userDetail = $user->getAllFieldsWithUserId($userId);
my $userName = $userDetail->{"userName"};

my $commoncfg = readConfig("main.conf");
my $dbh=DBI->connect("DBI:mysql:$commoncfg->{DATABASE}:$commoncfg->{DBHOST}",$commoncfg->{USERNAME},$commoncfg->{PASSWORD});

my $assemblyId = param ('assemblyId') || '';
my $ctgListDetails;
my $commentDetails;
undef $/;# enable slurp mode
my $html = <DATA>;
if ($assemblyId)
{
	my $assembly=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$assembly->execute($assemblyId);
	my @assembly = $assembly->fetchrow_array();

	my $target=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$target->execute($assembly[4]);
	my @target = $target->fetchrow_array();

	my $assemblyExtraIds;
	my $checkAsbGenome = $dbh->prepare("SELECT * FROM matrix,link WHERE link.type LIKE 'asbGenome' AND link.child = matrix.id AND link.parent = ?");
	$checkAsbGenome->execute($assemblyId);
	if ($checkAsbGenome->rows > 0)
	{
		while(my @checkAsbGenome=$checkAsbGenome->fetchrow_array())
		{
			$assemblyExtraIds->{$checkAsbGenome[0]} = $checkAsbGenome[2];
		}
	}
	my $numTotal = 0;
	my $sourceTotal;
	my $hideTotal;
	my $lengthTotal = 0;

	my $assemblyCtg = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? ORDER BY x,z,y");
	$assemblyCtg->execute($assemblyId);
	while (my @assemblyCtg = $assemblyCtg->fetchrow_array())
	{
		my $num = 0;
		my $source;
		my $hide;
		foreach (split ",", $assemblyCtg[8])
		{
			next unless ($_);
			$num++;
			$numTotal++;
			my $hideFlag = ($_ =~ /^-/) ? 1 : 0;
			$_ =~ s/[^a-zA-Z0-9]//g;
			my $assemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
			$assemblySeq->execute($_);
			my @assemblySeq = $assemblySeq->fetchrow_array();
			my $assemblySequence=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
			$assemblySequence->execute($assemblySeq[5]);
			my @assemblySequence = $assemblySequence->fetchrow_array();
			if (exists $assemblyExtraIds->{$assemblySequence[4]})
			{
				if (exists $source->{$assemblyExtraIds->{$assemblySequence[4]}})
				{
					$source->{$assemblyExtraIds->{$assemblySequence[4]}}++;
				}
				else
				{
					$source->{$assemblyExtraIds->{$assemblySequence[4]}} = 1;
				}
				if (exists $sourceTotal->{$assemblyExtraIds->{$assemblySequence[4]}})
				{
					$sourceTotal->{$assemblyExtraIds->{$assemblySequence[4]}}++;
				}
				else
				{
					$sourceTotal->{$assemblyExtraIds->{$assemblySequence[4]}} = 1;
				}
				if($hideFlag)
				{
					if (exists $hide->{$assemblyExtraIds->{$assemblySequence[4]}})
					{
						$hide->{$assemblyExtraIds->{$assemblySequence[4]}}++;
					}
					else
					{
						$hide->{$assemblyExtraIds->{$assemblySequence[4]}} = 1;
					}
					if (exists $hideTotal->{$assemblyExtraIds->{$assemblySequence[4]}})
					{
						$hideTotal->{$assemblyExtraIds->{$assemblySequence[4]}}++;
					}
					else
					{
						$hideTotal->{$assemblyExtraIds->{$assemblySequence[4]}} = 1;
					}
				}
			}
			else
			{
				if (exists $source->{$target[2]})
				{
					$source->{$target[2]}++;
				}
				else
				{
					$source->{$target[2]} = 1;
				}
				if (exists $sourceTotal->{$target[2]})
				{
					$sourceTotal->{$target[2]}++;
				}
				else
				{
					$sourceTotal->{$target[2]} = 1;
				}
				if($hideFlag)
				{
					if (exists $hide->{$target[2]})
					{
						$hide->{$target[2]}++;
					}
					else
					{
						$hide->{$target[2]} = 1;
					}
					if (exists $hideTotal->{$target[2]})
					{
						$hideTotal->{$target[2]}++;
					}
					else
					{
						$hideTotal->{$target[2]} = 1;
					}
				}
			}
		}
		my $sourceDetails = (exists $source->{$target[2]}) ? (exists $hide->{$target[2]}) ? "$target[2]:$source->{$target[2]}<sub title='hidden'>[-$hide->{$target[2]}]</sub>": "$target[2]:$source->{$target[2]}" : "";
		foreach (keys %$assemblyExtraIds)
		{
			if (exists $source->{$assemblyExtraIds->{$_}})
			{
				$sourceDetails .= ($sourceDetails) ? 
				(exists $hide->{$assemblyExtraIds->{$_}}) ? "; $assemblyExtraIds->{$_}:$source->{$assemblyExtraIds->{$_}}<sub title='hidden'>[-$hide->{$assemblyExtraIds->{$_}}]</sub>" : "; $assemblyExtraIds->{$_}:$source->{$assemblyExtraIds->{$_}}" : 
				(exists $hide->{$assemblyExtraIds->{$_}}) ? "$assemblyExtraIds->{$_}:$source->{$assemblyExtraIds->{$_}}<sub title='hidden'>[-$hide->{$assemblyExtraIds->{$_}}]</sub>" : "$assemblyExtraIds->{$_}:$source->{$assemblyExtraIds->{$_}}";
			}
		}

		my $chrName= '';
		if($assemblyCtg[4] == 0)
		{
			$chrName = "$assemblyCtg[4] = Unplaced";		
		}
		else
		{
			if ($assemblyCtg[4] % 100 == 98)
			{
				$chrName = "$assemblyCtg[4] = Chloroplast";
			}
			elsif($assemblyCtg[4] % 100 == 99)
			{
				$chrName = "$assemblyCtg[4] = Mitochondrion";
			}
			else
			{
				if($assemblyCtg[4] > 100)
				{
					my $subGenomeNumber = substr ($assemblyCtg[4], 0, -2);
					my $subChrNumber = sprintf "%0*d", 2, substr ($assemblyCtg[4], -2);
					$chrName = "$assemblyCtg[4] = Subgenome$subGenomeNumber-Chr$subChrNumber";
				}
				else
				{
					my $chrNumber = sprintf "%0*d", 2, $assemblyCtg[4];
					$chrName = "$assemblyCtg[4] = Chr$chrNumber";
				}
			}
		}
		$lengthTotal += $assemblyCtg[7];
		my $commentDescription;
		my $comment = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'comment' AND o = ?");
		$comment->execute($assemblyCtg[0]);
		my @comment = $comment->fetchrow_array();
		if ($comment->rows > 0)
		{
			$commentDetails = decode_json $comment[8];
			$commentDetails->{'description'} = '' unless (exists $commentDetails->{'description'});
			$ctgListDetails.="<tr><td>Ctg$assemblyCtg[2]</td><td>$num ($sourceDetails)</td><td>$chrName</td><td>".commify($assemblyCtg[7])."</td><td>$commentDetails->{'description'}</td></tr>" ;
		}
		else
		{
			$ctgListDetails.="<tr><td>Ctg$assemblyCtg[2]</td><td>$num ($sourceDetails)</td><td>$chrName</td><td>".commify($assemblyCtg[7])."</td><td></td></tr>" ;
		}
	}
	my $sourceTotalDetails = (exists $sourceTotal->{$target[2]}) ? (exists $hideTotal->{$target[2]}) ? "$target[2]:$sourceTotal->{$target[2]}<sub title='hidden'>[-$hideTotal->{$target[2]}]</sub>" : "$target[2]:$sourceTotal->{$target[2]}" : "";
	foreach (keys %$assemblyExtraIds)
	{
		if (exists $sourceTotal->{$assemblyExtraIds->{$_}})
		{
			$sourceTotalDetails .= ($sourceTotalDetails) ? 
			(exists $hideTotal->{$assemblyExtraIds->{$_}}) ? "; $assemblyExtraIds->{$_}:$sourceTotal->{$assemblyExtraIds->{$_}}<sub title='hidden'>[-$hideTotal->{$assemblyExtraIds->{$_}}]</sub>" : "; $assemblyExtraIds->{$_}:$sourceTotal->{$assemblyExtraIds->{$_}}" : 
			(exists $hideTotal->{$assemblyExtraIds->{$_}}) ? "$assemblyExtraIds->{$_}:$sourceTotal->{$assemblyExtraIds->{$_}}<sub title='hidden'>[-$hideTotal->{$assemblyExtraIds->{$_}}]</sub>" : "$assemblyExtraIds->{$_}:$sourceTotal->{$assemblyExtraIds->{$_}}";
		}
	}
	
	$ctgListDetails = "
	<table id='ctgLengthDetails$$' class='display'>
	<thead><tr><th><b>Contig</b></th><th><b>Number of assemblySeqs</b></th><th><b>Assigned chromosome #</b></th><th><b>Length (bp)</b></th><th><b>Comment</b></th></tr></thead>
	<tbody>$ctgListDetails</tbody>
	<tfoot><tr><th><b>Total</b></th><th>$numTotal ($sourceTotalDetails)</th><th><b></b></th><th>".commify($lengthTotal)."</th><th><b></b></th></tr></tfoot></table>
	";
	
}

$html =~ s/\$\$/$$/g;
$html =~ s/\$ctgListDetails/$ctgListDetails/g;
$html =~ s/\$assemblyId/$assemblyId/g;
$html =~ s/\$commoncfg->{HTDOCS}/$commoncfg->{HTDOCS}/g;
print header;
print $html;

__DATA__
<button style="float: right; margin-top: .3em; margin-right: .3em;" onclick="submitForm('assemblyCtg$assemblyId$$')">Download</button>
<button style="float: right; margin-top: .3em; margin-right: .3em;" onclick="printDiv('viewCtgLength$$')">Print</button>
<form id="assemblyCtg$assemblyId$$" name="assemblyCtg$assemblyId$$" action="download.cgi" enctype="multipart/form-data" method="post" target="hiddenFrame">
<input name="assemblyIdForCtgList" id="assemblyIdForCtgList" type="hidden" value="$assemblyId" />
<div id="viewCtgLength$$" name="viewCtgLength$$">
$ctgListDetails
</div>
</form>
<script>
buttonInit();
$( "#ctgLengthDetails$$" ).dataTable({
	"dom": 'lfrtip',
	"scrollY": "500px",
	"scrollCollapse": true,
	"paging": false,
	"searching": false,
	"ordering": false,
	"info": false
});
</script>