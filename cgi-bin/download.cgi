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
	97=>'Piece',
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

if (param ('seqId'))
{
	my $sequenceId = param ('seqId');
	my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$getSequences->execute($sequenceId);
	my @getSequences =  $getSequences->fetchrow_array();
	print header(-type=>'application/octet-stream',
		-attachment=> "$sequenceId-$getSequences[2]-$getSequences[3]-$getSequences[6].seq"
		);
	my $sequenceDetails = decode_json $getSequences[8];
	$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
	$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
	$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
	$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
	$getSequences[2] = $getSequences[0] unless ($getSequences[2]);
	print ">$getSequences[0]-$getSequences[4]-$getSequences[2]-$seqType{$getSequences[3]}-$getSequences[6] $getSequences[5] bp $sequenceDetails->{'id'} $sequenceDetails->{'description'}\n$sequenceDetails->{'sequence'}\n";
}
elsif (param ('jobId'))
{
	my $jobId = param ('jobId');
	my $seqTypeNumber =  param ('seqType') || "0";
	print header(-type=>'application/octet-stream',
		-attachment=> "job-$jobId.$seqTypeNumber.seq"
		);
	my $getSequences;
	if($seqTypeNumber eq '0')
	{
		$getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 0 AND x = ?");
	}
	elsif($seqTypeNumber eq '1')
	{
		$getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND (o = 1 OR o = 2) AND x = ?");
	}
	elsif($seqTypeNumber eq '3')
	{
		$getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 3 AND x = ?");
	}
	elsif($seqTypeNumber eq '4')
	{
		$getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 4 AND x = ?");
	}
	elsif($seqTypeNumber eq 'bacId')
	{
		$getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND name != '' AND x = ?");
	}
	else
	{
		$getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o < 50 AND x = ?");
	}
	$getSequences->execute($jobId);
	while(my @getSequences =  $getSequences->fetchrow_array())
	{
		my $sequenceDetails = decode_json $getSequences[8];
		$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
		$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
		$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
		$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
		$getSequences[2] = $getSequences[0] unless ($getSequences[2]);
		print ">$getSequences[0]-$getSequences[4]-$getSequences[2]-$seqType{$getSequences[3]}-$getSequences[6] $getSequences[5] bp $sequenceDetails->{'id'} $sequenceDetails->{'description'}\n$sequenceDetails->{'sequence'}\n";
	}		
}
elsif (param ('agpId'))
{
	my $agpId = param ('agpId');
	my $getAgp = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$getAgp->execute($agpId);
	my @getAgp =  $getAgp->fetchrow_array();
	print header(-type=>'application/octet-stream',
		-attachment=> "agp-$agpId.$getAgp[2].agp"
		);
	print $getAgp[8];
}
elsif(param ('libraryId'))
{
	my $libraryId = param ('libraryId');
	print header(-type=>'application/octet-stream',
		-attachment=>"library$libraryId.seq"
		);
	my $getClones = $dbh->prepare("SELECT * FROM clones WHERE libraryId = ? AND sequenced > 0 ORDER BY name");
	$getClones->execute($libraryId);
	while(my @getClones = $getClones->fetchrow_array())
	{
		my $getSequences;
		if($getClones[5])
		{
			$getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o < 50 AND (name LIKE ? OR name LIKE ?)");
			$getSequences->execute($getClones[1],$getClones[5]);
		}
		else
		{
			$getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o < 50 AND name LIKE ?");
			$getSequences->execute($getClones[1]);
		}
		while(my @getSequences =  $getSequences->fetchrow_array())
		{
			my $sequenceDetails = decode_json $getSequences[8];
			$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
			$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
			$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
			$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
			print ">$getSequences[0]-$getSequences[4]-$getClones[1]-$getSequences[2]-$seqType{$getSequences[3]}-$getSequences[6] $getSequences[5] bp $sequenceDetails->{'id'} $sequenceDetails->{'description'}\n$sequenceDetails->{'sequence'}\n";
		}		
	}
}
elsif(param ('seqLibraryId'))
{
	my $seqLibraryId = param ('seqLibraryId');
	print header(-type=>'application/octet-stream',
		-attachment=>"libraryPool$seqLibraryId.html"
		);

	my $library=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$library->execute($seqLibraryId);
	my @library = $library->fetchrow_array();
	my $pools = '';
	my $pool=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'pool' AND x = ? ORDER BY name");
	$pool->execute($seqLibraryId);
	while (my @pool = $pool->fetchrow_array())
	{
		$pools = "
		<table border='1' cellspacing='1' width='100%'>
        <thead>
            <tr>
                <th><b>Pool Name</b></th>
                <th><b>Pool Size</b></th>
                <th><b>Pooling BACs</b></th>
                <th><b>Original BACs</b></th>
                <th><b>Notes</b></th>
                <th><b>Assembly jobId</b></th>
            </tr>
        </thead>
        <tbody>"
		unless($pools);

		my $jobIds;
		my $jobId=$dbh->prepare("SELECT * FROM link WHERE parent = ? AND type LIKE 'poolJob' ORDER BY child DESC");
		$jobId->execute($pool[0]);
		while(my @jobId = $jobId->fetchrow_array())
		{
			$jobIds .= "$jobId[1] ";
		}
		$jobIds = "None" unless ($jobIds);

		my $clones;
		my $originalClones;
		my $sequencedNumber = 0;
		my $notSequencedNumber = 0;
		my $clone=$dbh->prepare("SELECT clones.* FROM link,clones WHERE link.type LIKE 'poolClone' AND link.child = clones.name AND link.parent = ? ORDER BY clones.name");
		$clone->execute($pool[0]);
		while(my @clone = $clone->fetchrow_array())
		{
			$clones .= "<a title='$clone[5]'>$clone[1]</a>($clone[6]) ";
			$originalClones .= ($clone[5]) ? "<a title='$clone[1]'>$clone[5]</a>($clone[6]) ": "";
			($clone[6]) ? $sequencedNumber++ : $notSequencedNumber++;
		}
		$clones = "None" unless ($clones);
		my $totalCloneNumber = $sequencedNumber + $notSequencedNumber;
		$pools .= ($notSequencedNumber > 0) ? "<tr><td><a title='Id:$pool[0]'>$pool[2]</a></td>
		<td>$totalCloneNumber</td>
		<td>$clones</td>
		<td>$originalClones</td>
		<td><sup>Sequenced: $sequencedNumber; Not sequenced: $notSequencedNumber.</sup><br>$pool[8]</td>
		<td>$jobIds</td></tr>" : "<tr><td><a title='Id:$pool[0]'>$pool[2]</a></td>
		<td>$totalCloneNumber</td>
		<td>$clones</td>
		<td>$originalClones</td>
		<td><sup>Sequenced: $sequencedNumber.</sup><br>$pool[8]</td>
		<td>$jobIds</td></tr>";
	}
	$pools .= "</tbody></table>\n" if ($pools);
	print $pools;
}
elsif(param ('besLibraryId'))
{
	my $besLibraryId = param ('besLibraryId');
	print header(-type=>'application/octet-stream',
		-attachment=>"BESofLibrary$besLibraryId.seq"
		);
	my $getSequences = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 98 AND x = ? ORDER BY name,id");
	$getSequences->execute($besLibraryId);
	while(my @getSequences =  $getSequences->fetchrow_array())
	{
		my $sequenceDetails = decode_json $getSequences[8];
		$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
		$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
		$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
		$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
		print ">$getSequences[0]-$getSequences[4]-$seqType{$getSequences[3]}-$getSequences[2].$seqDir{$getSequences[6]} $getSequences[5] bp $sequenceDetails->{'id'} $sequenceDetails->{'description'}\n$sequenceDetails->{'sequence'}\n";
	}		
}
elsif(param ('assemblyCtgId'))
{
	my $assemblyCtgId = param ('assemblyCtgId');
	my $pseudo = param ('pseudo') || 0;
	my $assemblyCtg=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$assemblyCtg->execute($assemblyCtgId);
	my @assemblyCtg = $assemblyCtg->fetchrow_array();
	print header(-type=>'application/octet-stream',
		-attachment=>"assemblyCtg$assemblyCtgId.Ctg$assemblyCtg[2].seq"
		);
	print ">Ctg$assemblyCtg[2] (" if($pseudo);
	my $ctgSequence = '';
	foreach (split ",", $assemblyCtg[8])
	{
		if(/^-/)
		{
			$pseudo and next;
			print ">HIDDEN-";
		}
		else
		{
			print ">" unless ($pseudo);
		}
		$_ =~ s/[^a-zA-Z0-9]//g;
		my $assemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$assemblySeq->execute($_);
		my @assemblySeq = $assemblySeq->fetchrow_array();
		my $assemblySequence=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$assemblySequence->execute($assemblySeq[5]);
		my @assemblySequence = $assemblySequence->fetchrow_array();
		my $sequenceDetails = decode_json $assemblySequence[8];
		$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
		$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
		$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
		$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
		$sequenceDetails->{'filter'} = '' unless (exists $sequenceDetails->{'filter'});
		if($pseudo)
		{
			if($ctgSequence)
			{
				print ",$assemblySeq[2].$assemblySeq[5]";
			}
			else
			{
				print "$assemblySeq[2].$assemblySeq[5]";
			}
			my $assemblySeqStart;
			my $assemblySeqEnd;
			
			if($assemblySeq[8])
			{
				($assemblySeqStart,$assemblySeqEnd) = split ",",$assemblySeq[8];
			}
			else
			{
				$assemblySeqStart = 1;
				$assemblySeqEnd = $assemblySeq[6];
				my $updateAssemblyClone=$dbh->do("UPDATE matrix SET note = '$assemblySeqStart,$assemblySeqEnd' WHERE id = $assemblySeq[0]");
			}
			if ($sequenceDetails->{'filter'})
			{
				my @filter = split",",$sequenceDetails->{'filter'};
				my @filterPos;
				my @position;
				my $start = $assemblySeqStart;
				my $end = $assemblySeqEnd;
				for my $filter(@filter)
				{
					@filterPos = split"-",$filter;
					next if ($assemblySeqStart > $filterPos[1]);
					last if ($assemblySeqEnd < $filterPos[0]);
					if ($assemblySeqStart >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
					{
						$start = 0;
						$assemblySeqEnd = 0;
						last;
					}
					if ($assemblySeqStart >= $filterPos[0] && $assemblySeqStart <= $filterPos[1])
					{
						$start = $filterPos[1]+1;
						next;
					}
					if ($assemblySeqEnd >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
					{
						$assemblySeqEnd = $filterPos[0]-1;
						last;
					}
					$end = $filterPos[0]-1;
					push @position,[$start,$end];
					$start = $filterPos[1]+1;
				}
				push @position,[$start,$assemblySeqEnd] if ($start > 0);
				if ($assemblySeq[7] =~ /^-/)
				{
					@position= reverse @position;
				}
				for my $position(@position)
				{
					$sequenceDetails->{'sequence'} =~ s/[^a-zA-Z0-9]//g;
					my $sequence = substr($sequenceDetails->{'sequence'}, $position->[0] - 1, $position->[1] - $position->[0] + 1);		
					$sequence = reverseComplement($sequence) if($assemblySeq[7] < 0);
					$ctgSequence .= "$sequence\n";
				}
			}
			else
			{
				$sequenceDetails->{'sequence'} =~ s/[^a-zA-Z0-9]//g;
				my $sequence = substr($sequenceDetails->{'sequence'}, $assemblySeqStart - 1, $assemblySeqEnd - $assemblySeqStart + 1);		
				$sequence = reverseComplement($sequence) if($assemblySeq[7] < 0);
				$ctgSequence .= "$sequence\n";
			}
		}
		else
		{
			print "$assemblySequence[2].$assemblySequence[0] $assemblySequence[4]-$seqType{$assemblySequence[3]} $assemblySequence[5] bp $sequenceDetails->{'id'} $sequenceDetails->{'description'}\n$sequenceDetails->{'sequence'}\n";
		}
	}
	print ")\n$ctgSequence" if($pseudo);
}
elsif(param ('assemblyCtgIdForAgp'))
{
	my $assemblyCtgIdForAgp = param ('assemblyCtgIdForAgp') || '';
	my $assemblyCtg = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$assemblyCtg->execute($assemblyCtgIdForAgp);
	my @assemblyCtg = $assemblyCtg->fetchrow_array();
	print header(-type=>'application/octet-stream',
		-attachment=>"Ctg$assemblyCtg[2].agp"
		);
	print "##agp-version 2.0\n";
	my $num = 1;
	my $begin = 1;
	for (split ",",$assemblyCtg[8])
	{
		/^-/ and next;
		$_ =~ s/[^a-zA-Z0-9]//g;
		my $assemblySeq = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$assemblySeq->execute($_);
		my @assemblySeq = $assemblySeq->fetchrow_array();
		my ($assemblySeqStart,$assemblySeqEnd) = split",",$assemblySeq[8];
		my $sequence = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
		$sequence->execute($assemblySeq[5]);
		my @sequence = $sequence->fetchrow_array();
		my $sequenceDetails = decode_json $sequence[8];
		$sequenceDetails->{'filter'} = '' unless (exists $sequenceDetails->{'filter'});
		my $orient = ($assemblySeq[7] =~ /^-/) ? '-' : '+';
		if ($sequenceDetails->{'filter'})
		{
			my @filter = split",",$sequenceDetails->{'filter'};
			my @filterPos;
			my @position;
			my $start = $assemblySeqStart;
			my $end = $assemblySeqEnd;
			for my $filter(@filter)
			{
				@filterPos = split"-",$filter;
				next if ($assemblySeqStart > $filterPos[1]);
				last if ($assemblySeqEnd < $filterPos[0]);
				if ($assemblySeqStart >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
				{
					$start = 0;
					$assemblySeqEnd = 0;
					last;
				}
				if ($assemblySeqStart >= $filterPos[0] && $assemblySeqStart <= $filterPos[1])
				{
					$start = $filterPos[1]+1;
					next;
				}
				if ($assemblySeqEnd >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
				{
					$assemblySeqEnd = $filterPos[0]-1;
					last;
				}
				$end = $filterPos[0]-1;
				push @position,[$start,$end];
				$start = $filterPos[1]+1;
			}
			push @position,[$start,$assemblySeqEnd] if ($start > 0);
			if ($assemblySeq[7] =~ /^-/)
			{
				@position= reverse @position;
			}
			my $seqLength = 0;
			for my $position(@position)
			{
				$seqLength=$position->[1]-$position->[0]+1;
				if($sequence[3] > 50) #not BAC sequence
				{
					print "Ctg$assemblyCtg[2]\t$begin\t",$begin+$seqLength-1,"\t$num\tD\t$assemblySeq[2]\t$position->[0]\t$position->[1]\t$orient\n";
				}
				else
				{
					print "Ctg$assemblyCtg[2]\t$begin\t",$begin+$seqLength-1,"\t$num\tD\t$assemblySeq[2]\.$assemblySeq[5]\t$position->[0]\t$position->[1]\t$orient\n";
				}
				$begin += $seqLength;
				$num++;
			}
		}
		else
		{
			if($sequence[3] > 50) #not BAC sequence
			{
				print "Ctg$assemblyCtg[2]\t$begin\t",$begin+$assemblySeqEnd-$assemblySeqStart,"\t$num\tD\t$assemblySeq[2]\t$assemblySeqStart\t$assemblySeqEnd\t$orient\n";
			}
			else
			{
				print "Ctg$assemblyCtg[2]\t$begin\t",$begin+$assemblySeqEnd-$assemblySeqStart,"\t$num\tD\t$assemblySeq[2]\.$assemblySeq[5]\t$assemblySeqStart\t$assemblySeqEnd\t$orient\n";
			}
			$begin += $assemblySeqEnd-$assemblySeqStart+1;
			$num++;
		}
	}
}
elsif(param ('assemblyId'))
{
	my $assemblyId = param ('assemblyId');
	my $chr = param('chr') || 'all'; 
	my $unit = param('unit') || 'ctg'; 
	my $assembly=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$assembly->execute($assemblyId);
	my @assembly = $assembly->fetchrow_array();
	print header(-type=>'application/octet-stream',
		-attachment=>"assembly$assemblyId.$assembly[2].Chr$chr.$unit.seq"
		);
	if($unit eq 'chr')
	{
		my $preChr = 'na';
		my $chrSequence;
		my $assemblyCtg=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? ORDER BY x,z");
		$assemblyCtg->execute($assemblyId);
		while(my @assemblyCtg = $assemblyCtg->fetchrow_array())
		{
			if ($chr ne 'all')
			{
				 next if ($chr ne $assemblyCtg[4]);
			}

			if($assemblyCtg[4] == 0)
			{
				print ">Ctg$assemblyCtg[2] (";
				my $ctgSequence = '';
				foreach (split ",", $assemblyCtg[8])
				{
					/^-/ and next;
					$_ =~ s/[^a-zA-Z0-9]//g;
					my $assemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$assemblySeq->execute($_);
					my @assemblySeq = $assemblySeq->fetchrow_array();
					my $assemblySequence=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$assemblySequence->execute($assemblySeq[5]);
					my @assemblySequence = $assemblySequence->fetchrow_array();
					my $sequenceDetails = decode_json $assemblySequence[8];
					$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
					$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
					$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
					$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
					$sequenceDetails->{'filter'} = '' unless (exists $sequenceDetails->{'filter'});
					if($ctgSequence)
					{
						print ",$assemblySeq[2].$assemblySeq[5]";
					}
					else
					{
						print "$assemblySeq[2].$assemblySeq[5]";
					}
					$sequenceDetails->{'sequence'} =~ s/[^a-zA-Z0-9]//g;
					my $assemblySeqStart;
					my $assemblySeqEnd;
					if($assemblySeq[8])
					{
						($assemblySeqStart,$assemblySeqEnd) = split ",",$assemblySeq[8];
					}
					else
					{
						$assemblySeqStart = 1;
						$assemblySeqEnd = $assemblySeq[6];
						my $updateAssemblyClone=$dbh->do("UPDATE matrix SET note = '$assemblySeqStart,$assemblySeqEnd' WHERE id = $assemblySeq[0]");
					}
					if ($sequenceDetails->{'filter'})
					{
						my @filter = split",",$sequenceDetails->{'filter'};
						my @filterPos;
						my @position;
						my $start = $assemblySeqStart;
						my $end = $assemblySeqEnd;
						for my $filter(@filter)
						{
							@filterPos = split"-",$filter;
							next if ($assemblySeqStart > $filterPos[1]);
							last if ($assemblySeqEnd < $filterPos[0]);
							if ($assemblySeqStart >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
							{
								$start = 0;
								$assemblySeqEnd = 0;
								last;
							}
							if ($assemblySeqStart >= $filterPos[0] && $assemblySeqStart <= $filterPos[1])
							{
								$start = $filterPos[1]+1;
								next;
							}
							if ($assemblySeqEnd >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
							{
								$assemblySeqEnd = $filterPos[0]-1;
								last;
							}
							$end = $filterPos[0]-1;
							push @position,[$start,$end];
							$start = $filterPos[1]+1;
						}
						push @position,[$start,$assemblySeqEnd] if ($start > 0);
						if ($assemblySeq[7] =~ /^-/)
						{
							@position= reverse @position;
						}
						for my $position(@position)
						{
							my $sequence = substr($sequenceDetails->{'sequence'}, $position->[0] - 1, $position->[1] - $position->[0] + 1);		
							$sequence = reverseComplement($sequence) if($assemblySeq[7] < 0);
							$ctgSequence .= "$sequence\n";
						}
					}
					else
					{
						my $sequence = substr($sequenceDetails->{'sequence'}, $assemblySeqStart - 1, $assemblySeqEnd - $assemblySeqStart + 1);		
						$sequence = reverseComplement($sequence) if($assemblySeq[7] < 0);
						$ctgSequence .= "$sequence\n";
					}
				}
				print ")\n$ctgSequence";
			}
			else
			{
				if ($preChr ne $assemblyCtg[4])
				{
					my $chrNumber = sprintf "%0*d", 2, $assemblyCtg[4];
					print ")\n$chrSequence->{$preChr}" if ($preChr ne 'na');
					print ">Chr$chrNumber (";
					$preChr = $assemblyCtg[4];
					$chrSequence->{$assemblyCtg[4]} = 'N'x100 . "\n";  #left telomere
				}
				if(length ($chrSequence->{$assemblyCtg[4]}) > 101)
				{
					print ";Ctg$assemblyCtg[2]-";
				}
				else
				{
					print "Ctg$assemblyCtg[2]-";
				}
				my $ctgSequence = '';
				foreach (split ",", $assemblyCtg[8])
				{
					/^-/ and next;
					$_ =~ s/[^a-zA-Z0-9]//g;
					my $assemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$assemblySeq->execute($_);
					my @assemblySeq = $assemblySeq->fetchrow_array();
					my $assemblySequence=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$assemblySequence->execute($assemblySeq[5]);
					my @assemblySequence = $assemblySequence->fetchrow_array();
					my $sequenceDetails = decode_json $assemblySequence[8];
					$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
					$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
					$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
					$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
					$sequenceDetails->{'filter'} = '' unless (exists $sequenceDetails->{'filter'});
					if($ctgSequence)
					{
						print ",$assemblySeq[2].$assemblySeq[5]";
					}
					else
					{
						print "$assemblySeq[2].$assemblySeq[5]";
					}
					$sequenceDetails->{'sequence'} =~ s/[^a-zA-Z0-9]//g;
					my $assemblySeqStart;
					my $assemblySeqEnd;
					if($assemblySeq[8])
					{
						($assemblySeqStart,$assemblySeqEnd) = split ",",$assemblySeq[8];
					}
					else
					{
						$assemblySeqStart = 1;
						$assemblySeqEnd = $assemblySeq[6];
						my $updateAssemblyClone=$dbh->do("UPDATE matrix SET note = '$assemblySeqStart,$assemblySeqEnd' WHERE id = $assemblySeq[0]");
					}
					if ($sequenceDetails->{'filter'})
					{
						my @filter = split",",$sequenceDetails->{'filter'};
						my @filterPos;
						my @position;
						my $start = $assemblySeqStart;
						my $end = $assemblySeqEnd;
						for my $filter(@filter)
						{
							@filterPos = split"-",$filter;
							next if ($assemblySeqStart > $filterPos[1]);
							last if ($assemblySeqEnd < $filterPos[0]);
							if ($assemblySeqStart >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
							{
								$start = 0;
								$assemblySeqEnd = 0;
								last;
							}
							if ($assemblySeqStart >= $filterPos[0] && $assemblySeqStart <= $filterPos[1])
							{
								$start = $filterPos[1]+1;
								next;
							}
							if ($assemblySeqEnd >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
							{
								$assemblySeqEnd = $filterPos[0]-1;
								last;
							}
							$end = $filterPos[0]-1;
							push @position,[$start,$end];
							$start = $filterPos[1]+1;
						}
						push @position,[$start,$assemblySeqEnd] if ($start > 0);
						if ($assemblySeq[7] =~ /^-/)
						{
							@position= reverse @position;
						}
						for my $position(@position)
						{
							my $sequence = substr($sequenceDetails->{'sequence'}, $position->[0] - 1, $position->[1] - $position->[0] + 1);		
							$sequence = reverseComplement($sequence) if($assemblySeq[7] < 0);
							$ctgSequence .= "$sequence\n";
						}
					}
					else
					{
						my $sequence = substr($sequenceDetails->{'sequence'}, $assemblySeqStart - 1, $assemblySeqEnd - $assemblySeqStart + 1);		
						$sequence = reverseComplement($sequence) if($assemblySeq[7] < 0);
						$ctgSequence .= "$sequence\n";
					}
				}
				$chrSequence->{$assemblyCtg[4]} .= "$ctgSequence" .  'N'x100 . "\n";
			}
		}
		print ")\n$chrSequence->{$preChr}" if ($preChr ne 'na');
	}
	else
	{
		my $assemblyCtg=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? ORDER BY x,z");
		$assemblyCtg->execute($assemblyId);
		while(my @assemblyCtg = $assemblyCtg->fetchrow_array())
		{
			if ($chr ne 'all')
			{
				 next if ($chr ne $assemblyCtg[4]);
			}
			print ">Ctg$assemblyCtg[2] (";
			my $ctgSequence = '';
			foreach (split ",", $assemblyCtg[8])
			{
				/^-/ and next;
				$_ =~ s/[^a-zA-Z0-9]//g;
				my $assemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
				$assemblySeq->execute($_);
				my @assemblySeq = $assemblySeq->fetchrow_array();
				my $assemblySequence=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
				$assemblySequence->execute($assemblySeq[5]);
				my @assemblySequence = $assemblySequence->fetchrow_array();
				my $sequenceDetails = decode_json $assemblySequence[8];
				$sequenceDetails->{'id'} = '' unless (exists $sequenceDetails->{'id'});
				$sequenceDetails->{'description'} = '' unless (exists $sequenceDetails->{'description'});
				$sequenceDetails->{'sequence'} = '' unless (exists $sequenceDetails->{'sequence'});
				$sequenceDetails->{'gapList'} = '' unless (exists $sequenceDetails->{'gapList'});
				$sequenceDetails->{'filter'} = '' unless (exists $sequenceDetails->{'filter'});
				if($ctgSequence)
				{
					print ",$assemblySeq[2].$assemblySeq[5]";
				}
				else
				{
					print "$assemblySeq[2].$assemblySeq[5]";
				}
				$sequenceDetails->{'sequence'} =~ s/[^a-zA-Z0-9]//g;
				my $assemblySeqStart;
				my $assemblySeqEnd;
				if($assemblySeq[8])
				{
					($assemblySeqStart,$assemblySeqEnd) = split ",",$assemblySeq[8];
				}
				else
				{
					$assemblySeqStart = 1;
					$assemblySeqEnd = $assemblySeq[6];
					my $updateAssemblyClone=$dbh->do("UPDATE matrix SET note = '$assemblySeqStart,$assemblySeqEnd' WHERE id = $assemblySeq[0]");
				}
				if ($sequenceDetails->{'filter'})
				{
					my @filter = split",",$sequenceDetails->{'filter'};
					my @filterPos;
					my @position;
					my $start = $assemblySeqStart;
					my $end = $assemblySeqEnd;
					for my $filter(@filter)
					{
						@filterPos = split"-",$filter;
						next if ($assemblySeqStart > $filterPos[1]);
						last if ($assemblySeqEnd < $filterPos[0]);
						if ($assemblySeqStart >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
						{
							$start = 0;
							$assemblySeqEnd = 0;
							last;
						}
						if ($assemblySeqStart >= $filterPos[0] && $assemblySeqStart <= $filterPos[1])
						{
							$start = $filterPos[1]+1;
							next;
						}
						if ($assemblySeqEnd >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
						{
							$assemblySeqEnd = $filterPos[0]-1;
							last;
						}
						$end = $filterPos[0]-1;
						push @position,[$start,$end];
						$start = $filterPos[1]+1;
					}
					push @position,[$start,$assemblySeqEnd] if ($start > 0);
					if ($assemblySeq[7] =~ /^-/)
					{
						@position= reverse @position;
					}
					for my $position(@position)
					{
						my $sequence = substr($sequenceDetails->{'sequence'}, $position->[0] - 1, $position->[1] - $position->[0] + 1);		
						$sequence = reverseComplement($sequence) if($assemblySeq[7] < 0);
						$ctgSequence .= "$sequence\n";
					}
				}
				else
				{
					my $sequence = substr($sequenceDetails->{'sequence'}, $assemblySeqStart - 1, $assemblySeqEnd - $assemblySeqStart + 1);		
					$sequence = reverseComplement($sequence) if($assemblySeq[7] < 0);
					$ctgSequence .= "$sequence\n";
				}
			}
			print ")\n$ctgSequence";
		}
	}
}
elsif(param ('assemblyIdForAgp'))
{
	my $assemblyIdForAgp = param ('assemblyIdForAgp');
	my $chr = param('chr') || 'all'; 
	my $unit = param('unit') || 'ctg'; 
	my $element = param('element') || 'seq'; 
	my $assembly=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$assembly->execute($assemblyIdForAgp);
	my @assembly = $assembly->fetchrow_array();
	print header(-type=>'application/octet-stream',
		-attachment=>"assembly$assemblyIdForAgp.$assembly[2].Chr$chr.$unit-$element.agp"
		);
	print "##agp-version 2.0\n";
	if($unit eq 'chr')
	{
		my $preChr = 'na';
		my $chrUn = 1;
		my $num;
		$num->{0} = 1;
		my $begin;
		$begin->{0} = 1;
		my $gapLength = 100;
		my $assemblyCtg=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? ORDER BY x,z");
		$assemblyCtg->execute($assemblyIdForAgp);
		while(my @assemblyCtg = $assemblyCtg->fetchrow_array())
		{
			if ($chr ne 'all')
			{
				 next if ($chr ne $assemblyCtg[4]);
			}

			if($assemblyCtg[4] == 0)
			{
				my $chrUnNumber = sprintf "%0*d", 2, $chrUn;
				$chrUn++;
				if($element eq 'seq')
				{
					for (split ",", $assemblyCtg[8])
					{
						/^-/ and next;
						$_ =~ s/[^a-zA-Z0-9]//g;
						my $assemblySeq = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$assemblySeq->execute($_);
						my @assemblySeq = $assemblySeq->fetchrow_array();
						my ($assemblySeqStart,$assemblySeqEnd) = split",",$assemblySeq[8];
						my $sequence = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$sequence->execute($assemblySeq[5]);
						my @sequence = $sequence->fetchrow_array();
						my $sequenceDetails = decode_json $sequence[8];
						$sequenceDetails->{'filter'} = '' unless (exists $sequenceDetails->{'filter'});
						my $orient = ($assemblySeq[7] =~ /^-/) ? '-' : '+';
						if ($sequenceDetails->{'filter'})
						{
							my @filter = split",",$sequenceDetails->{'filter'};
							my @filterPos;
							my @position;
							my $start = $assemblySeqStart;
							my $end = $assemblySeqEnd;
							for my $filter(@filter)
							{
								@filterPos = split"-",$filter;
								next if ($assemblySeqStart > $filterPos[1]);
								last if ($assemblySeqEnd < $filterPos[0]);
								if ($assemblySeqStart >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
								{
									$start = 0;
									$assemblySeqEnd = 0;
									last;
								}
								if ($assemblySeqStart >= $filterPos[0] && $assemblySeqStart <= $filterPos[1])
								{
									$start = $filterPos[1]+1;
									next;
								}
								if ($assemblySeqEnd >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
								{
									$assemblySeqEnd = $filterPos[0]-1;
									last;
								}
								$end = $filterPos[0]-1;
								push @position,[$start,$end];
								$start = $filterPos[1]+1;
							}
							push @position,[$start,$assemblySeqEnd] if ($start > 0);
							if ($assemblySeq[7] =~ /^-/)
							{
								@position= reverse @position;
							}
							my $seqLength = 0;
							for my $position(@position)
							{
								$seqLength=$position->[1]-$position->[0]+1;
								if($sequence[3] > 50) #not BAC sequence
								{
									print "ChrUN$chrUnNumber\t$begin->{0}\t",$begin->{0}+$seqLength-1,"\t$num->{0}\tD\t$assemblySeq[2]\t$position->[0]\t$position->[1]\t$orient\n";
								}
								else
								{
									print "ChrUN$chrUnNumber\t$begin->{0}\t",$begin->{0}+$seqLength-1,"\t$num->{0}\tD\t$assemblySeq[2]\.$assemblySeq[5]\t$position->[0]\t$position->[1]\t$orient\n";
								}
								$begin->{0} += $seqLength;
								$num->{0}++;
							}
						}
						else
						{
							if($sequence[3] > 50) #not BAC sequence
							{
								print "ChrUN$chrUnNumber\t$begin->{0}\t",$begin->{0}+$assemblySeqEnd-$assemblySeqStart,"\t$num->{0}\tD\t$assemblySeq[2]\t$assemblySeqStart\t$assemblySeqEnd\t$orient\n";
							}
							else
							{
								print "ChrUN$chrUnNumber\t$begin->{0}\t",$begin->{0}+$assemblySeqEnd-$assemblySeqStart,"\t$num->{0}\tD\t$assemblySeq[2]\.$assemblySeq[5]\t$assemblySeqStart\t$assemblySeqEnd\t$orient\n";
							}
							$begin->{0} += $assemblySeqEnd-$assemblySeqStart+1;
							$num->{0}++;
						}
					}
				}
				else
				{
					 #element eq 'ctg'
					print "ChrUN$chrUnNumber\t1\t",$assemblyCtg[7],"\t$num->{0}\tD\tCtg$assemblyCtg[2]\t1\t$assemblyCtg[7]\t+\n";
				}
			}
			else
			{
				my $chrNumber = sprintf "%0*d", 2, $assemblyCtg[4];
				if ($preChr ne $chrNumber)
				{
					if($preChr ne "na")
					{
						#right telomere
						$num->{$preChr}++;
						print "Chr$preChr\t$begin->{$preChr}\t",$begin->{$preChr}+$gapLength-1,"\t$num->{$preChr}\tU\t$gapLength\ttelomere\tno\tna\n";
						$begin->{$preChr} += $gapLength;
					}
					$preChr = $chrNumber;
					$begin->{$chrNumber} = 1;
					$num->{$chrNumber} = 1;
					#left telomere
					print "Chr$chrNumber\t$begin->{$chrNumber}\t",$begin->{$chrNumber}+$gapLength-1,"\t$num->{$chrNumber}\tU\t$gapLength\ttelomere\tno\tna\n";
					$begin->{$chrNumber} += $gapLength;
				}
				else
				{
					#right gap
					$num->{$chrNumber}++;
					print "Chr$chrNumber\t$begin->{$chrNumber}\t",$begin->{$chrNumber}+$gapLength-1,"\t$num->{$chrNumber}\tU\t$gapLength\tcontig\tno\tna\n";
					$begin->{$chrNumber} += $gapLength;
				}

				#sequence
				if($element eq 'seq')
				{
					for (split ",", $assemblyCtg[8])
					{
						/^-/ and next;
						$_ =~ s/[^a-zA-Z0-9]//g;
						my $assemblySeq = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$assemblySeq->execute($_);
						my @assemblySeq = $assemblySeq->fetchrow_array();
						my ($assemblySeqStart,$assemblySeqEnd) = split",",$assemblySeq[8];
						my $sequence = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
						$sequence->execute($assemblySeq[5]);
						my @sequence = $sequence->fetchrow_array();
						my $sequenceDetails = decode_json $sequence[8];
						$sequenceDetails->{'filter'} = '' unless (exists $sequenceDetails->{'filter'});
						my $orient = ($assemblySeq[7] =~ /^-/) ? '-' : '+';
						if ($sequenceDetails->{'filter'})
						{
							my @filter = split",",$sequenceDetails->{'filter'};
							my @filterPos;
							my @position;
							my $start = $assemblySeqStart;
							my $end = $assemblySeqEnd;
							for my $filter(@filter)
							{
								@filterPos = split"-",$filter;
								next if ($assemblySeqStart > $filterPos[1]);
								last if ($assemblySeqEnd < $filterPos[0]);
								if ($assemblySeqStart >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
								{
									$start = 0;
									$assemblySeqEnd = 0;
									last;
								}
								if ($assemblySeqStart >= $filterPos[0] && $assemblySeqStart <= $filterPos[1])
								{
									$start = $filterPos[1]+1;
									next;
								}
								if ($assemblySeqEnd >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
								{
									$assemblySeqEnd = $filterPos[0]-1;
									last;
								}
								$end = $filterPos[0]-1;
								push @position,[$start,$end];
								$start = $filterPos[1]+1;
							}
							push @position,[$start,$assemblySeqEnd] if ($start > 0);
							if ($assemblySeq[7] =~ /^-/)
							{
								@position= reverse @position;
							}
							my $seqLength = 0;
							for my $position(@position)
							{
								$seqLength=$position->[1]-$position->[0]+1;
								$num->{$chrNumber}++;
								if($sequence[3] > 50) #not BAC sequence
								{
									print "Chr$chrNumber\t$begin->{$chrNumber}\t",$begin->{$chrNumber}+$seqLength-1,"\t$num->{$chrNumber}\tD\t$assemblySeq[2]\t$position->[0]\t$position->[1]\t$orient\n";
								}
								else
								{
									print "Chr$chrNumber\t$begin->{$chrNumber}\t",$begin->{$chrNumber}+$seqLength-1,"\t$num->{$chrNumber}\tD\t$assemblySeq[2]\.$assemblySeq[5]\t$position->[0]\t$position->[1]\t$orient\n";
								}
								$begin->{$chrNumber} += $seqLength;
							}
						}
						else
						{
							$num->{$chrNumber}++;
							if($sequence[3] > 50) #not BAC sequence
							{
								print "Chr$chrNumber\t$begin->{$chrNumber}\t",$begin->{$chrNumber}+$assemblySeqEnd-$assemblySeqStart,"\t$num->{$chrNumber}\tD\t$assemblySeq[2]\t$assemblySeqStart\t$assemblySeqEnd\t$orient\n";
							}
							else
							{
								print "Chr$chrNumber\t$begin->{$chrNumber}\t",$begin->{$chrNumber}+$assemblySeqEnd-$assemblySeqStart,"\t$num->{$chrNumber}\tD\t$assemblySeq[2]\.$assemblySeq[5]\t$assemblySeqStart\t$assemblySeqEnd\t$orient\n";
							}
							$begin->{$chrNumber} += $assemblySeqEnd-$assemblySeqStart+1;
						}
					}
				}
				else
				{
					#element eq 'ctg'
					$num->{$chrNumber}++;
					print "Chr$chrNumber\t$begin->{$chrNumber}\t",$begin->{$chrNumber}+$assemblyCtg[7]-1,"\t$num->{$chrNumber}\tD\tCtg$assemblyCtg[2]\t1\t$assemblyCtg[7]\t+\n";
					$begin->{$chrNumber} += $assemblyCtg[7];
				}
			}
		}
		if($preChr ne "na")
		{
			#right telomere
			$num->{$preChr}++;
			print "Chr$preChr\t$begin->{$preChr}\t",$begin->{$preChr}+$gapLength-1,"\t$num->{$preChr}\tU\t$gapLength\ttelomere\tno\tna\n";
			$begin->{$preChr} += $gapLength;
		}
	}
	else
	{
		my $assemblyCtg=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND o = ? ORDER BY x,z");
		$assemblyCtg->execute($assemblyIdForAgp);
		while(my @assemblyCtg = $assemblyCtg->fetchrow_array())
		{
			if ($chr ne 'all')
			{
				 next if ($chr ne $assemblyCtg[4]);
			}
			my $num = 1;
			my $begin = 1;
			for (split ",", $assemblyCtg[8])
			{
				/^-/ and next;
				$_ =~ s/[^a-zA-Z0-9]//g;
				my $assemblySeq = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
				$assemblySeq->execute($_);
				my @assemblySeq = $assemblySeq->fetchrow_array();
				my ($assemblySeqStart,$assemblySeqEnd) = split",",$assemblySeq[8];
				my $sequence = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
				$sequence->execute($assemblySeq[5]);
				my @sequence = $sequence->fetchrow_array();
				my $sequenceDetails = decode_json $sequence[8];
				$sequenceDetails->{'filter'} = '' unless (exists $sequenceDetails->{'filter'});
				my $orient = ($assemblySeq[7] =~ /^-/) ? '-' : '+';
				if ($sequenceDetails->{'filter'})
				{
					my @filter = split",",$sequenceDetails->{'filter'};
					my @filterPos;
					my @position;
					my $start = $assemblySeqStart;
					my $end = $assemblySeqEnd;
					for my $filter(@filter)
					{
						@filterPos = split"-",$filter;
						next if ($assemblySeqStart > $filterPos[1]);
						last if ($assemblySeqEnd < $filterPos[0]);
						if ($assemblySeqStart >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
						{
							$start = 0;
							$assemblySeqEnd = 0;
							last;
						}
						if ($assemblySeqStart >= $filterPos[0] && $assemblySeqStart <= $filterPos[1])
						{
							$start = $filterPos[1]+1;
							next;
						}
						if ($assemblySeqEnd >= $filterPos[0] && $assemblySeqEnd <= $filterPos[1])
						{
							$assemblySeqEnd = $filterPos[0]-1;
							last;
						}
						$end = $filterPos[0]-1;
						push @position,[$start,$end];
						$start = $filterPos[1]+1;
					}
					push @position,[$start,$assemblySeqEnd] if ($start > 0);
					if ($assemblySeq[7] =~ /^-/)
					{
						@position= reverse @position;
					}
					my $seqLength = 0;
					for my $position(@position)
					{
						$seqLength=$position->[1]-$position->[0]+1;
						if($sequence[3] > 50) #not BAC sequence
						{
							print "Ctg$assemblyCtg[2]\t$begin\t",$begin+$seqLength-1,"\t$num\tD\t$assemblySeq[2]\t$position->[0]\t$position->[1]\t$orient\n";
						}
						else
						{
							print "Ctg$assemblyCtg[2]\t$begin\t",$begin+$seqLength-1,"\t$num\tD\t$assemblySeq[2]\.$assemblySeq[5]\t$position->[0]\t$position->[1]\t$orient\n";
						}
						$begin += $seqLength;
						$num++;
					}
				}
				else
				{
					if($sequence[3] > 50) #not BAC sequence
					{
						print "Ctg$assemblyCtg[2]\t$begin\t",$begin+$assemblySeqEnd-$assemblySeqStart,"\t$num\tD\t$assemblySeq[2]\t$assemblySeqStart\t$assemblySeqEnd\t$orient\n";
					}
					else
					{
						print "Ctg$assemblyCtg[2]\t$begin\t",$begin+$assemblySeqEnd-$assemblySeqStart,"\t$num\tD\t$assemblySeq[2]\.$assemblySeq[5]\t$assemblySeqStart\t$assemblySeqEnd\t$orient\n";
					}
					$begin += $assemblySeqEnd-$assemblySeqStart+1;
					$num++;
				}
			}
		}
	}
}
else
{
	print header(-type=>'text/html',-status=>'402 Invalid operation');
}
