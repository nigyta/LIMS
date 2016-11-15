#!/usr/bin/perl -w
use strict;
use CGI qw(:standard);
use CGI::Carp qw ( fatalsToBrowser ); 
use JSON; #JSON::XS is recommended to be installed for handling JSON string of big size 
use DBI;
use SVG;
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

undef $/;# enable slurp mode
my $html = <DATA>;

my $assemblyId = param ('assemblyId') || '';
my $assemblyStatus;
$assemblyStatus->{2} = "Frozen";
$assemblyStatus->{1} = "Assembled";
$assemblyStatus->{0} = "Initialized";
$assemblyStatus->{-1} = "Assembling...";
$assemblyStatus->{-2} = "SeqToSeq Aligning...";
$assemblyStatus->{-3} = "Physical Reference-based Assembling...";
$assemblyStatus->{-4} = "SeqToGenome Aligning...";
$assemblyStatus->{-5} = "Assigning Chr#...";
$assemblyStatus->{-6} = "Filtering Seqs...";
$assemblyStatus->{-7} = "Orienting Seqs...";
$assemblyStatus->{-8} = "Orienting Contigs...";
$assemblyStatus->{-9} = "EndToEnd Merging...";
$assemblyStatus->{-10} = "Filtering Overlaps...";
$assemblyStatus->{-11} = "Estimating Length...";
$assemblyStatus->{-12} = "BesToSeq Aligning...";
my $autoSeqSearchUrl = 'autoSeqSearch.cgi';
if($assemblyId)
{
	$autoSeqSearchUrl .= "?assemblyId=$assemblyId";
}

my $assemblyList = '';
my $assemblySortableStyle = '';
my $assemblySortableJs = '';
my $totalLength;
$totalLength->{'all'} = 0;
my @lengthList;
my $maxLength;
$maxLength->{'all'} = 0;
my $minLength;
my $button;
$minLength->{'all'} = 999999999;
if ($assemblyId)
{
	my $assembly=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$assembly->execute($assemblyId);
	my @assembly = $assembly->fetchrow_array();

	my $assemblyDetails = decode_json $assembly[8];
	$assemblyDetails->{'autoCheckNewSeq'} = 0 if (!exists $assemblyDetails->{'autoCheckNewSeq'});
	$assemblyDetails->{'log'} = 'None.' if (!exists $assemblyDetails->{'log'});
	$assemblyDetails->{'log'} = escapeHTML($assemblyDetails->{'log'});
	$assemblyDetails->{'log'} =~ s/\n/<br>/g;

	my $target=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$target->execute($assembly[4]);
	my @target = $target->fetchrow_array();

	my $gapFillerViewer = '';
	$gapFillerViewer = "<li><a onclick='openDialog(\"$commoncfg->{TMPURL}/$assemblyId.gapfill.html\")'><span class='ui-icon ui-icon-bullet'></span>View</a></li>" if (-e "$commoncfg->{TMPDIR}/$assemblyId.gapfill.html");
	my $gapFillerDownload = '';
	$gapFillerDownload = "<li><a href='$commoncfg->{TMPURL}/$assemblyId.gapfill.txt.gz' target='hiddenFrame'><span class='ui-icon ui-icon-bullet'></span>Download</a></li>" if (-e "$commoncfg->{TMPDIR}/$assemblyId.gapfill.txt.gz");
	$assemblyList .= "<ul class='assemblyMenu' style='left: 0px;top: 0px;display:inline-block;width: 200px;'>
				<li><a><span class='ui-icon ui-icon-wrench'></span>Assembly Tools</a>
					<ul style='z-index: 1000;white-space: nowrap;'>
						<li><a onclick='openDialog(\"assemblyEdit.cgi?assemblyId=$assemblyId\")'><span class='ui-icon ui-icon-pencil'></span>Edit This Assembly</a></li>
						<li><a onclick='openDialog(\"assemblyValidation.cgi?assemblyId=$assemblyId\")'><span class='ui-icon ui-icon-search'></span>Validate This Assembly</a></li>
						<li><a onclick='openDialog(\"assemblyAssign.cgi?assemblyId=$assemblyId\")'><span class='ui-icon ui-icon-arrow-2-e-w'></span>Assign Ctg To Chromosome</a></li>
						<li><a><span class='ui-icon ui-icon-disk'></span>Download</a>
							<ul style='z-index: 1000;white-space: nowrap;'>";
	$assemblyList .= ($target[1] eq 'library') ? "<li><a href='download.cgi?libraryId=$assembly[4]' target='hiddenFrame'><span class='ui-icon ui-icon-bullet'></span>BAC Sequence</a></li>
						<li><a href='download.cgi?besLibraryId=$assembly[4]' target='hiddenFrame'><span class='ui-icon ui-icon-bullet'></span>BAC End Sequence</a></li>"
						: "";

	$assemblyList .= "<li><a href='download.cgi?assemblyId=$assemblyId&chr=all' target='hiddenFrame'><span class='ui-icon ui-icon-bullet'></span>Ctg PseudoMolecules</a></li>
						<li><a href='download.cgi?assemblyId=$assemblyId&chr=all&unit=chr' target='hiddenFrame'><span class='ui-icon ui-icon-bullet'></span>Chr PseudoMolecules</a></li>
						<li><a href='download.cgi?assemblyIdForAgp=$assemblyId&chr=all' target='hiddenFrame'><span class='ui-icon ui-icon-bullet'></span>Ctg-Seq AGP</a></li>
						<li><a href='download.cgi?assemblyIdForAgp=$assemblyId&chr=all&unit=chr&element=ctg' target='hiddenFrame'><span class='ui-icon ui-icon-bullet'></span>Chr-Ctg AGP</a></li>
						<li><a href='download.cgi?assemblyIdForAgp=$assemblyId&chr=all&unit=chr' target='hiddenFrame'><span class='ui-icon ui-icon-bullet'></span>Chr-Seq AGP</a></li>
							</ul>
						</li>
						<li><a><span class='ui-icon ui-icon-transfer-e-w'></span>Alignment</a>
							<ul style='z-index: 1000;white-space: nowrap;'>
								<li><a onclick='openDialog(\"assemblySeqToSeqForm.cgi?assemblyId=$assemblyId\")'><span class='ui-icon ui-icon-bullet'></span>Seq to Seq</a></li>
								<li><a onclick='openDialog(\"assemblySeqToGenomeForm.cgi?assemblyId=$assemblyId\")'><span class='ui-icon ui-icon-bullet'></span>Seq to Genome</a></li>";
	$assemblyList .= ($target[1] eq 'library') ? "<li><a onclick='openDialog(\"besToSeqForm.cgi?libraryId=$assembly[4]&targetId=$assembly[5]\")'><span class='ui-icon ui-icon-bullet'></span>BES to Seq</a></li>" 
						: ($target[6] > 0) ? "<li><a onclick='openDialog(\"besToSeqForm.cgi?libraryId=$target[6]&targetId=$assembly[5]\")'><span class='ui-icon ui-icon-bullet'></span>BES to Seq</a></li>" 
						: "";
	$assemblyList .= "</ul>
						</li>
						<li><a onclick='openDialog(\"assemblyRunForm.cgi?assemblyId=$assemblyId\")'><span class='ui-icon ui-icon-shuffle'></span>Run Assembly</a></li>
						<li><a><span class='ui-icon ui-icon-link'></span>Gap Filler</a>
							<ul style='z-index: 1000;white-space: nowrap;'>
								<li><a onclick='openDialog(\"assemblyGapFillForm.cgi?assemblyId=$assemblyId\")'><span class='ui-icon ui-icon-bullet'></span>Run</a></li>
								$gapFillerViewer
								$gapFillerDownload
							</ul>
						</li>
						<li><a onclick='printDiv(\"assemblyTab$assemblyId$$\")'><span class='ui-icon ui-icon-print'></span>Print</a></li>
					</ul>
				</li>
			</ul>";
			
	$assemblyList .= ($assembly[7] < 1) ? "<button style='float: right;' onclick='refresh(\"menu\")' title='Click to Refresh'>Status: $assemblyStatus->{$assembly[7]}</button>" : 
							($assembly[7] == 1) ? "<button style='float: right;' onclick='loaddiv(\"hiddenDiv\", \"assemblyFreeze.cgi?assemblyId=$assemblyId\")' title='Click to Freeze'>$assemblyStatus->{$assembly[7]}</button>
							<button style='float: right;' onclick='refresh(\"menu\")'>Refresh</button>" :
							"<button style='float: right;' onclick='loaddiv(\"hiddenDiv\", \"assemblyFreeze.cgi?assemblyId=$assemblyId\")' title='Click to Unfreeze'>$assemblyStatus->{$assembly[7]}</button>
							<button style='float: right;' onclick='refresh(\"menu\")'>Refresh</button>";
	$assemblyList .= "<input style='float: right;'  class='ui-widget-content ui-corner-all' name='seqName' id='assemblySearchSeqName$$' size='16' type='text' maxlength='32' VALUE='' placeholder='Search Seq' />
			<hr>";
	my $assemblySeq;
	my $assemblyCtg;
	my $assemblyCtgNumber = 0;
	my $assemblyCtgChr;
	my $assemblyCtgChrOrder;
	my $assemblyCtgLength;
	my $assemblyCtgSeqNumber;
    my $totalAssembled = 0;
	my $inCtgSeq;
	my $assemblyCtgs = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ?");
	$assemblyCtgs->execute($assembly[0]);
	while(my @assemblyCtgs = $assemblyCtgs->fetchrow_array())
	{
		$assemblyCtg->{$assemblyCtgs[0]} = $assemblyCtgs[2];
		$assemblyCtgNumber = $assemblyCtgs[2] if($assemblyCtgs[2] > $assemblyCtgNumber);
		$assemblyCtgChr->{$assemblyCtgs[0]} = $assemblyCtgs[4];
		$assemblyCtgChrOrder->{$assemblyCtgs[0]} = ($assemblyCtgs[4]) ? $assemblyCtgs[5] : $assemblyCtgs[2];
		$assemblyCtgLength->{$assemblyCtgs[0]} = $assemblyCtgs[7];
		$totalLength->{'all'} += $assemblyCtgs[7];
		push @lengthList,$assemblyCtgs[7];
		$maxLength->{'all'} = $assemblyCtgs[7] if ($assemblyCtgs[7] > $maxLength->{'all'});
		$minLength->{'all'} = $assemblyCtgs[7] if ($assemblyCtgs[7] < $minLength->{'all'});
		my @seqs = split ",", $assemblyCtgs[8];
		$assemblyCtgSeqNumber->{$assemblyCtgs[0]} = @seqs;
		for (@seqs)
		{
			next unless ($_);
			$_ =~ s/[^a-zA-Z0-9]//g;
			$inCtgSeq->{$_} = 1;
		}
		$totalAssembled++;
	}
	my $assemblySeqs = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblySeq' AND o = ?");
	$assemblySeqs->execute($assembly[0]);
	while(my @assemblySeqs = $assemblySeqs->fetchrow_array())
	{
		$assemblySeq->{$assemblySeqs[5]} = $assemblySeqs[4];
	}

	@lengthList = sort {$b <=> $a} @lengthList;
	my $median = int ($#lengthList/2);
	my $medianLength = $lengthList[$median];
	my $n50Length = 0;
	my $subtotal = 0;
	my $margin = 20;
	my $chartWidth = 600;
	my $chartHeight = 400;
	my $svgWidth = $chartWidth + $margin*2;
	my $svgHeight = $chartHeight + $margin*2;
	my $widthUnit = int ($maxLength->{'all'}/ $chartWidth) || 1; 
	my $heightUnit = ($totalAssembled > 0) ? $chartHeight/$totalAssembled : 0; 
	my $assemblyCtgLengthCount;
	foreach (@lengthList)
	{
		$subtotal += $_;
		if($subtotal > $totalLength->{'all'}/2 && $n50Length == 0)
		{
			$n50Length = $_;
		}
		for (my $i = 1; $i <= $_; $i += $widthUnit)
		{
			$assemblyCtgLengthCount->{$i} = 0 unless (exists $assemblyCtgLengthCount->{$i});
			$assemblyCtgLengthCount->{$i}++;
		}
		
	}
	my $graphic = '';
	if ($totalLength->{'all'} > 0)
	{
		# create an SVG object
		my $svg= SVG->new(width=>$svgWidth,height=>$svgHeight); # set width and height after knowing the size
		# use explicit element constructor to generate a group element
		my $length=$svg->group(
			id    => 'length',
			style => { stroke=>'black',
				fill =>'white'
			}
		);
		$length->rectangle(
				x=> $margin, y=> $margin,
				width=>$chartWidth, height=>$chartHeight,
				id=>'rect_1'
			);
		my $stringOfContigNumber = ($#lengthList > 0) ? "Total ". commify($#lengthList + 1) ." contigs" : "Total ". commify($#lengthList + 1) ." contig";
		my $lengthOfContigNumber = length ($stringOfContigNumber);
		my $xPositionOfContigNumber = $margin - 5;
		my $yPositionOfContigNumber = $lengthOfContigNumber * 7;
		$length->text(
				id      => 'totalContigs',
				x       => $xPositionOfContigNumber,
				y       => $yPositionOfContigNumber,
				style=>{
					stroke=>'black',
				fill =>'black'
				},
				transform => "rotate(-90,$xPositionOfContigNumber,$yPositionOfContigNumber)"
			)->cdata($stringOfContigNumber);

		$length->text(
				id      => 'minLength',
				x       => 0,
				y       => $svgHeight - 5,
				style=>{
					stroke=>'black',
				fill =>'black'
				}
			)->cdata("Shortest: ". commify($minLength->{'all'}) . " bp");

		my $lengthOfString = length ("Longest: ". commify($maxLength->{'all'}) . " bp");
		$length->text(
				id      => 'maxLength',
				x       => $svgWidth - $lengthOfString * 8,
				y       => $svgHeight - 5,
				style=>{
					stroke=>'black',
				fill =>'black'
				}
			)->cdata("Longest: ". commify($maxLength->{'all'}) . " bp");

		my $n50y = 0;
		my $mediany = 0;
		my @xvArray;
		my @yvArray;
		for (sort {$a <=> $b} keys %$assemblyCtgLengthCount)
		{
			push @xvArray, $_ / $widthUnit + $margin;
			push @yvArray, $chartHeight - $heightUnit * $assemblyCtgLengthCount->{$_}  + $margin;
			$n50y  = $chartHeight - $heightUnit * $assemblyCtgLengthCount->{$_}  + $margin if( $n50Length > $_);
			$mediany  = $chartHeight - $heightUnit * $assemblyCtgLengthCount->{$_} + $margin if( $medianLength > $_);
		}
		my $xv = [@xvArray];
		my $yv = [@yvArray];
		my $points = $length->get_path(
			x=>$xv, y=>$yv,
			-type=>'polyline',
			-closed=>'false' #specify that the polyline is closed.
		);
		$length->polyline (
			%$points,
			id=>'pline_1',
			style=>{
				'fill-opacity'=>0,
				'stroke-color'=>'rgb(250,123,23)'
			}
		);

		$length->line(
				id=>'mediana',
				style => {
					stroke=> 'lightgrey',
					'stroke-dasharray' => '3,3'
					},
				x1=>$medianLength / $widthUnit  + $margin, y1=>$mediany,
				x2=>$medianLength / $widthUnit  + $margin, y2=>$chartHeight + $margin
			);
# 		$length->line(
# 				id=>'medianb',
# 				x1=> $margin, y1=>$mediany,
# 				x2=>$medianLength / $widthUnit + $margin, y2=>$mediany
# 			);
		$length->text(
				id      => 'mediantext',
				x       => $medianLength / $widthUnit  + $margin,
				y       => $mediany,
				style=>{
					stroke=>'black',
				fill =>'black'
				}
			)->cdata("Median: ". commify($medianLength) . " bp");

		$length->line(
				id=>'n50a',
				style => {
					stroke=> 'lightgrey',
					'stroke-dasharray' => '3,3'
					},
				x1=>$n50Length / $widthUnit + $margin, y1=>$n50y,
				x2=>$n50Length / $widthUnit + $margin, y2=>$chartHeight + $margin
			);
# 		$length->line(
# 				id=>'n50b',
# 				x1=> $margin, y1=>$n50y,
# 				x2=>$n50Length / $widthUnit + $margin, y2=>$n50y
# 			);
		$length->text(
				id      => 'n50text',
				x       => $n50Length / $widthUnit + $margin,
				y       => $n50y,
				style=>{
					stroke=>'black',
				fill =>'black'
				}
			)->cdata("N50: ". commify($n50Length) . " bp");

		# now render the SVG object, implicitly use svg namespace
		$graphic = $svg->xmlify;
	}

	my @assemblyCtg = sort { $assemblyCtgChrOrder->{$a} <=> $assemblyCtgChrOrder->{$b} } keys %$assemblyCtgChrOrder;
	my $assembledCtgByChr;
	my $totalAssembledContigByChr;
	my $totalAssembledSeqNumberByChr;
	my $assemblySortableJsByChr;
	my $assemblySortableStyleByChr;
	my $assemblyCtgOrders;
    for (@assemblyCtg)
    {
		my %commentType = (
			0=>"<a style='float: right;' onclick='closeDialog();openDialog(\"comment.cgi?itemId=$_\")'><span style=' left: 0px;top: 0px;display:inline-block;' class='ui-icon ui-icon-comment' title='Comments'></span></a>",
			1=>"<a style='float: right;' class='ui-state-error-text' onclick='closeDialog();openDialog(\"comment.cgi?itemId=$_\")'><span style=' left: 0px;top: 0px;display:inline-block;' class='ui-icon ui-icon-alert' title='Comments'></span></a>",
			2=>"<a style='float: right;' class='ui-state-error-text' onclick='closeDialog();openDialog(\"comment.cgi?itemId=$_\")'><span style=' left: 0px;top: 0px;display:inline-block;' class='ui-icon ui-icon-heart' title='Comments'></span></a>"
			);
		my $comment = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'comment' AND o = ?");
		$comment->execute($_);
		my $commentIcon;
		if ($comment->rows > 0)
		{
			my @comment = $comment->fetchrow_array();
			$commentIcon = $commentType{$comment[4]};
		}
		else
		{
			$commentIcon = "<a style='float: right;' class='ui-state-disabled' onclick='closeDialog();openDialog(\"comment.cgi?itemId=$_\")'><span style=' left: 0px;top: 0px;display:inline-block;' class='ui-icon ui-icon-comment' title='Add Comments'></span></a>";
		}
    	$assembledCtgByChr->{$assemblyCtgChr->{$_}} = "<form id='assemblyChr$assemblyId$assemblyCtgChr->{$_}' name='assemblyChr$assemblyId$assemblyCtgChr->{$_}' action='assemblyCtgOrder.cgi' enctype='multipart/form-data' method='post' target='hiddenFrame'><input name='assemblyId' id='assemblyId' type='hidden' value='$assemblyId' /><ul id='sortableCtgList$assemblyId$assemblyCtgChr->{$_}'>" unless (exists $assembledCtgByChr->{$assemblyCtgChr->{$_}});
		$assembledCtgByChr->{$assemblyCtgChr->{$_}} .= ($assemblyCtgSeqNumber->{$_} > 1) ?
				"<li class='ui-state-default' id='$_'>$commentIcon<a onclick='closeViewer();openViewer(\"assemblyCtgView.cgi?assemblyCtgId=$_\")'>Ctg$assemblyCtg->{$_} ($assemblyCtgSeqNumber->{$_})</a><br>" . commify($assemblyCtgLength->{$_}). " bp</li>"
				: "<li class='ui-state-default' id='$_'>$commentIcon<a onclick='closeViewer();openViewer(\"assemblyCtgView.cgi?assemblyCtgId=$_\")'>Ctg$assemblyCtg->{$_}</a><br>" . commify($assemblyCtgLength->{$_}). " bp</li>";
		
		$totalLength->{$assemblyCtgChr->{$_}} = 0 unless (exists $totalLength->{$assemblyCtgChr->{$_}});
		$totalLength->{$assemblyCtgChr->{$_}} += $assemblyCtgLength->{$_};
		$maxLength->{$assemblyCtgChr->{$_}} = 0 unless (exists $maxLength->{$assemblyCtgChr->{$_}});
		$maxLength->{$assemblyCtgChr->{$_}} = $assemblyCtgLength->{$_} if ($assemblyCtgLength->{$_} > $maxLength->{$assemblyCtgChr->{$_}});
		$minLength->{$assemblyCtgChr->{$_}} = 999999 unless (exists $minLength->{$assemblyCtgChr->{$_}});
		$minLength->{$assemblyCtgChr->{$_}} = $assemblyCtgLength->{$_} if ($assemblyCtgLength->{$_} < $minLength->{$assemblyCtgChr->{$_}});
    	$totalAssembledContigByChr->{$assemblyCtgChr->{$_}} = 0 unless (exists $totalAssembledContigByChr->{$assemblyCtgChr->{$_}});
		$totalAssembledSeqNumberByChr->{$assemblyCtgChr->{$_}} = 0 unless (exists $totalAssembledSeqNumberByChr->{$assemblyCtgChr->{$_}});
		$totalAssembledContigByChr->{$assemblyCtgChr->{$_}}++;
		$totalAssembledSeqNumberByChr->{$assemblyCtgChr->{$_}} += $assemblyCtgSeqNumber->{$_};

    	$assemblyCtgOrders->{$assemblyCtgChr->{$_}} = '' unless (exists $assemblyCtgOrders->{$assemblyCtgChr->{$_}});
    	$assemblyCtgOrders->{$assemblyCtgChr->{$_}} .= ($assemblyCtgOrders->{$assemblyCtgChr->{$_}}) ? ",$_" : $_;

    	$assemblySortableJsByChr->{$assemblyCtgChr->{$_}} = <<END;
			\$( "#sortableCtgList$assemblyId$assemblyCtgChr->{$_}" ).sortable({
				  placeholder: "ui-state-highlight",
				  forcePlaceholderSize: true,
				  stop: function(event, ui) {
					var oldSortedIds = \$('#assemblyCtgOrders$assemblyId$assemblyCtgChr->{$_}').val();
					var newSortedIds = \$( "#sortableCtgList$assemblyId$assemblyCtgChr->{$_}" ).sortable( "toArray" );
					if(oldSortedIds != newSortedIds)
					{
						savingShow();
						\$('#assemblyCtgOrders$assemblyId$assemblyCtgChr->{$_}').val(newSortedIds);
						submitForm('assemblyChr$assemblyId$assemblyCtgChr->{$_}');
					}
				}
			});
			\$( "#sortableCtgList$assemblyId$assemblyCtgChr->{$_}" ).disableSelection();
END
    	$assemblySortableStyleByChr->{$assemblyCtgChr->{$_}} = <<END;
		  <style>
		  #sortableCtgList$assemblyId$assemblyCtgChr->{$_} { list-style-type: none; display:inline-block;margin: 0; padding: 0; width: 100%; }
		  #sortableCtgList$assemblyId$assemblyCtgChr->{$_} li { margin: 3px 3px 3px 0; padding: 1px; float: left; width: 120px; text-align: center; }
		  </style>
END
    }
    my $assembledCtgDetails = '';
    for (sort {$b <=> $a} keys %$assembledCtgByChr)
    {
		$assembledCtgByChr->{$_} .= "</ul><input name='assemblyCtgOrders' id='assemblyCtgOrders$assemblyId$_' type='hidden' value='$assemblyCtgOrders->{$_}' /></form>";
		my $headerByChr;
		$headerByChr->{$_} = ($_ > 0 && $assembly[5] > 0) ?
			"<h3><a onclick='closeViewer();openViewer(\"assemblyChrView.cgi?assemblyId=$assemblyId&chr=$_\")'>Chromosome $_</a>"
			: "<h3>Chromosome $_";

		$headerByChr->{$_} .= ($totalAssembledContigByChr->{$_} > 1) ?
			" ($totalAssembledContigByChr->{$_} Contigs)"
			: " ($totalAssembledContigByChr->{$_} Contig)";

		$headerByChr->{$_} .= ($totalAssembledSeqNumberByChr->{$_} > 1) ?
			" - $totalAssembledSeqNumberByChr->{$_} Seqs"
			: " - $totalAssembledSeqNumberByChr->{$_} Seq";

		$headerByChr->{$_} .= ($totalAssembledContigByChr->{$_} > 1) ?
			" <sup>" . commify($totalLength->{$_}). " bp <ul class='assemblyMenu' style='width: 150px;display:inline-block; white-space: nowrap;'><li><a><span class='ui-icon ui-icon-disk'></span>Download</a><ul style='z-index: 1000;white-space: nowrap;'><li><a href='download.cgi?assemblyId=$assemblyId&chr=$_' target='hiddenFrame' title='Click to Download'><span class='ui-icon ui-icon-bullet'></span>Ctg Pseudomolecules</a></li>"
			: " <sup>" . commify($totalLength->{$_}). " bp <ul class='assemblyMenu' style='width: 150px;display:inline-block; white-space: nowrap;'><li><a><span class='ui-icon ui-icon-disk'></span>Download</a><ul style='z-index: 1000;white-space: nowrap;'><li><a href='download.cgi?assemblyId=$assemblyId&chr=$_' target='hiddenFrame' title='Click to Download'><span class='ui-icon ui-icon-bullet'></span>Ctg Pseudomolecule</a></li>";

		$headerByChr->{$_} .= ($_ > 0) ?
			"<li><a href='download.cgi?assemblyId=$assemblyId&chr=$_&unit=chr' target='hiddenFrame' title='Click to Download'><span class='ui-icon ui-icon-bullet'></span>Chr Pseudomolecule</a></li><li><a href='download.cgi?assemblyIdForAgp=$assemblyId&chr=$_' target='hiddenFrame' title='Click to Download'><span class='ui-icon ui-icon-bullet'></span>Ctg-Seq AGP</a></li><li><a href='download.cgi?assemblyIdForAgp=$assemblyId&chr=$_&unit=chr&element=ctg' target='hiddenFrame' title='Click to Download'><span class='ui-icon ui-icon-bullet'></span>Chr-Ctg AGP</a></li><li><a href='download.cgi?assemblyIdForAgp=$assemblyId&chr=$_&unit=chr' target='hiddenFrame' title='Click to Download'><span class='ui-icon ui-icon-bullet'></span>Chr-Seq AGP</a></li></ul></li></ul></sup></h3>"
			: "<li><a href='download.cgi?assemblyIdForAgp=$assemblyId&chr=$_' target='hiddenFrame' title='Click to Download'><span class='ui-icon ui-icon-bullet'></span>Ctg-Seq AGP</a></li></ul></li><li><a class='ui-state-error-text' onclick='deleteItem($assemblyId,\"chrZeroOnly\")' title='Delete Chr0 Contigs'><span class='ui-icon ui-icon-bullet'></span>Delete Chr0 Ctgs</a></li></ul></sup></h3>";

		$assembledCtgDetails = ($_ > 0) ? $headerByChr->{$_}.$assembledCtgByChr->{$_}.$assembledCtgDetails : $assembledCtgDetails.$headerByChr->{$_}.$assembledCtgByChr->{$_}; #list chromosome-assigned first.
		$assemblySortableStyle .= $assemblySortableStyleByChr->{$_};
		$assemblySortableJs .= $assemblySortableJsByChr->{$_};
    }
	my $assembledCtg = ($totalAssembled > 0) ? "<div id='tabs-assembled$assemblyId$$'>Total length: " . commify($totalLength->{'all'}). " bp, N50 length: " . commify($n50Length). " bp, Median length: " . commify($medianLength). " bp.<br>Longest: " . commify($maxLength->{'all'}). " bp, Shortest: " . commify($minLength->{'all'}). " bp.<br>$graphic $assembledCtgDetails</div>"
			: "<div id='tabs-assembled$assemblyId$$'>No assembly! Please run assembly!</div>";


	my $totalInAssembly = keys %$assemblySeq;
	$assemblyList .= "<div id='assemblyTab$assemblyId$$'><ul>";
	$assemblyList .= ($totalAssembled > 1) ? "<li><a href='#tabs-assembled$assemblyId$$'>Assembly ($totalAssembled Contigs)" : "<li><a href='#tabs-assembled$assemblyId$$'>Assembly ($totalAssembled Contig)";
	$assemblyList .= ($totalInAssembly > 1) ? " - $totalInAssembly Sequences</a></li>" : " - $totalInAssembly Sequence</a></li>";
	$assemblyList .= ($totalAssembled > 0) ? "<li><a href='assemblyCtgList.cgi?assemblyId=$assemblyId'>Contig List</a></li>" : "";

	if($assemblyDetails->{'autoCheckNewSeq'})
	{
		my $totalSequenced = 0;
		if($target[1] eq 'library')
		{
			my $getClones = $dbh->prepare("SELECT * FROM clones WHERE libraryId = ? AND sequenced > 0");
			$getClones->execute($assembly[4]);
			while(my @getClones= $getClones->fetchrow_array())
			{
				my $getSeqs = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o < 50 AND name LIKE ? ORDER BY id");
				$getSeqs->execute($getClones[1]);
				while(my @getSeqs = $getSeqs->fetchrow_array())
				{
					next if (exists $assemblySeq->{$getSeqs[0]});
					$totalSequenced++;
				}
				last if ($totalSequenced > 1);
			}
		}
		if($target[1] eq 'genome')
		{
			my $getSeqs = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = ? ORDER BY name");
			$getSeqs->execute($assembly[4]);
			while(my @getSeqs = $getSeqs->fetchrow_array())
			{
				next if (exists $assemblySeq->{$getSeqs[0]});
				$totalSequenced++;
				last if ($totalSequenced > 1);
			}
		}
		if($totalSequenced)
		{
			$assemblyList .= ($totalSequenced > 1) ? "<li><a href='assemblyCheckSeq.cgi?assemblyId=$assemblyId'>New Sequences Available</a></li>" : "<li><a href='assemblyCheckSeq.cgi?assemblyId=$assemblyId'>New Sequence Available</a></li>";
		}
	}
	else
	{
		$assemblyList .= "<li><a href='assemblyCheckSeq.cgi?assemblyId=$assemblyId'>Check New Sequences</a></li>";
	}

	$assemblyList .= "<li><a href='#tabs-assemblyLog$assemblyId$$'>Logs</a></li>";
	
	$assemblyList .= "</ul>$assembledCtg <div id='tabs-assemblyLog$assemblyId$$'>$assemblyDetails->{'log'}</div> $assemblySortableStyle</div>";
	$html =~ s/\$assemblyList/$assemblyList/g;
	$html =~ s/\$assemblyId/$assemblyId/g;
	$html =~ s/\$assemblySortableJs/$assemblySortableJs/g;
	$html =~ s/\$autoSeqSearchUrl/$autoSeqSearchUrl/g;
	$html =~ s/\$commoncfg->{HTDOCS}/$commoncfg->{HTDOCS}/g;
	$html =~ s/\$\$/$$/g;

	print header(-cookie=>cookie(-name=>'assembly',-value=>$assemblyId));
	print $html;
}
else
{
	print header(-type=>'text/html',-status=>'402 Invalid operation');
	exit;
}

__DATA__
$assemblyList
<script>
buttonInit();
$("#assemblyTab$assemblyId$$").tabs({
	// loading spinner
	beforeLoad: function(event, ui) {
		ui.panel.html('<img src="$commoncfg->{HTDOCS}/css/images/loading.gif" style="vertical-align:middle;"> Loading...');
	},
	active: 0
});
$( ".assemblyMenu" ).menu();
$( "#assemblySearchSeqName$$" ).autocomplete({
	source: "$autoSeqSearchUrl",
	minLength: 3,
	select: function( event, ui ) {
		openDialog("seqView.cgi?seqId=" + ui.item.id);
	}
});
$assemblySortableJs
loadingHide();

</script>
