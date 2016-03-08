#!/usr/bin/perl -w
use strict;
use CGI qw(:standard);
use CGI::Carp qw ( fatalsToBrowser ); 
use JSON;
use DBI;
use lib "lib/";
use lib "lib/pangu";
use pangu;
use user;
use config;
use userCookie;

my $userCookie = new userCookie;
my $userId = (cookie('cid')) ? $userCookie->checkCookie(cookie('cid')) : 0;
exit if (!$userId);

my $user = new user;
my $userDetail = $user->getAllFieldsWithUserId($userId);
my $userName = $userDetail->{"userName"};

my $commoncfg = readConfig("main.conf");
my $dbh=DBI->connect("DBI:mysql:$commoncfg->{DATABASE}:$commoncfg->{DBHOST}",$commoncfg->{USERNAME},$commoncfg->{PASSWORD});

my %smrtrunStatus = (
	0=>'Initialized',
	1=>'Started',
	2=>'Completed'
	);
my @items = param ('items');

my $config = new config;
my $userPermission;
my $userInGroup=$dbh->prepare("SELECT * FROM link WHERE type LIKE 'group' AND child = ?");
$userInGroup->execute($userId);
while (my @userInGroup = $userInGroup->fetchrow_array())
{
	my $group = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$group->execute($userInGroup[0]);
	my @group=$group->fetchrow_array();
	my $groupDetails = decode_json $group[8];
	$groupDetails->{'permission'} = '' unless (exists $groupDetails->{'permission'});
	for(split (",",$groupDetails->{'permission'}))
	{
		my $permission = $config->getFieldName($_);
		$userPermission->{$userId}->{$permission} = 1;		
	}
}
print header;

my $libraryId = 0;
for(@items)
{
	my $item = $dbh->prepare("SELECT * FROM matrix WHERE id = ?");
	$item->execute($_);
	my @item=$item->fetchrow_array();
	if($item[9] eq $userName || exists $userPermission->{$userId}->{'item'})
	{
		if($item[1] eq 'room')
		{
			my $freezerInRoom = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'freezer' AND o = $_");
			$freezerInRoom->execute();
			if ($freezerInRoom->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete freezers in the room first!");
</script>	
END
				exit;
			}
			my $deleteRoom=$dbh->do("DELETE FROM matrix WHERE id = $_");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
</script>	
END
		}
		elsif($item[1] eq 'freezer')
		{
			my $boxInFreezer = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'box' AND o = $_");
			$boxInFreezer->execute();
			if ($boxInFreezer->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete boxes in the freezer first!");
</script>	
END
				exit;
			}
			my $deleteFreezer=$dbh->do("DELETE FROM matrix WHERE id = $_");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
</script>	
END
		}
		elsif($item[1] eq 'box')
		{
			my $itemInBox = $dbh->prepare("SELECT * FROM link WHERE type LIKE 'box' AND parent = $_");
			$itemInBox->execute();
			if ($itemInBox->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Items in the box will become orphans!");
</script>	
END
			}
			my $deleteBox=$dbh->do("DELETE FROM matrix WHERE id = $_");
			my $deleteLinkA=$dbh->do("DELETE FROM link WHERE parent = $_ AND type LIKE 'box'");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
</script>	
END
		}
		elsif($item[1] eq "project")
		{
			my $serviceInProject = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'service' AND z = $_");
			$serviceInProject->execute();
			if($serviceInProject->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related services first!");
</script>	
END
				exit;
			}

			my $libraryInProject = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'library' AND z = $_");
			$libraryInProject->execute();
			if($libraryInProject->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related libraries first!");
</script>	
END
				exit;
			}
			my $deleteProject=$dbh->do("DELETE FROM matrix WHERE id = $_");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
</script>	
END
		}
		elsif($item[1] eq 'asbProject')
		{
			my $deleteAsbProject=$dbh->do("DELETE FROM matrix WHERE id = $_");
			my $deleteLink=$dbh->do("DELETE FROM link WHERE parent = $_ AND type LIKE 'asbProject'");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
</script>	
END
		}
		elsif($item[1] eq 'assembly')
		{

			my $deleteAssembly=$dbh->do("DELETE FROM matrix WHERE id = $_");
			my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE container LIKE 'assemblyCtg' AND o = $_");
			my $deleteAssemblySeq=$dbh->do("DELETE FROM matrix WHERE container LIKE 'assemblySeq' AND o = $_");
			#delete comment
			#to be added
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
</script>	
END
		}
		elsif($item[1] eq 'assemblyCtg')
		{
			my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $_");
			foreach (split ",", $item[8])
			{
				$_ =~ s/[^a-zA-Z0-9]//g;
				my $deleteAssemblySeq=$dbh->do("DELETE FROM matrix WHERE id = $_");
			}
			my $deleteComment=$dbh->do("DELETE FROM matrix WHERE container LIKE 'comment' AND o = $_");

			print <<END;
<script>
	parent.closeDialog();
	parent.closeViewer();
	parent.refresh("menu");
</script>	
END
		}
		elsif($item[1] eq 'assemblySeq')
		{
			my $scrollLeft = param ('scrollLeft') || '0';
			my $assemblyCtgOfSeq = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblyCtg' AND MATCH (note) AGAINST (?)");
			$assemblyCtgOfSeq->execute("($_)");
			my @assemblyCtgOfSeq = $assemblyCtgOfSeq->fetchrow_array();
			my @seqList = split ",", $assemblyCtgOfSeq[8];
			my $number=@seqList;
			my @newSeqList;
			my $seqId;
			if ($number > 1)
			{
				for (@seqList)
				{
					$seqId=$_;
					$_ =~ s/[^a-zA-Z0-9]//g;
					if (/$_/)
					{
						next;
					}
					else
					{
						push @newSeqList, $seqId;
					}
				}
				my $newCloneList = join ",", @newSeqList;
				my $updateAssemblyCtg=$dbh->do("UPDATE matrix SET note = '$newCloneList' WHERE id = $assemblyCtgOfSeq[0]");
				my $deleteAssemblySeq=$dbh->do("DELETE FROM matrix WHERE id = $_");
				print <<END;
<script>
parent.closeViewer();
parent.openViewer("assemblyCtgView.cgi?assemblyCtgId=$assemblyCtgOfSeq[0]&scrollLeft=$scrollLeft");
//parent.refresh("menu");
</script>	
END
			}
			else
			{
				my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $assemblyCtgOfSeq[0]");
				my $deleteAssemblySeq=$dbh->do("DELETE FROM matrix WHERE id = $_");
				my $deleteComment=$dbh->do("DELETE FROM matrix WHERE container LIKE 'comment' AND o = $assemblyCtgOfSeq[0]");
				print <<END;
<script>
	parent.closeDialog();
	parent.closeViewer();
	parent.refresh("menu");
</script>	
END
			}
			
		}
		elsif($item[1] eq 'sequence')
		{
			my $assemblySeq=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assemblySeq' AND y = ?");
			$assemblySeq->execute($_);
			my @assemblySeq = $assemblySeq->fetchrow_array();
			if ($assemblySeq->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related assemblies using this sequence first!");
</script>	
END
			}
			else
			{
				my $deleteAssemblyCtg=$dbh->do("DELETE FROM matrix WHERE id = $_");
				if ($item[3] eq '99' )
				{
					my $genome=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
					$genome->execute($item[4]);
					my @genome = $genome->fetchrow_array();
					$genome[3] = $genome[3]-1;

					my $updateGenome=$dbh->do("UPDATE matrix SET o = '$genome[3]' WHERE id = $item[4]");
				}
				print <<END;
<script>
	parent.closeDialog();
	parent.closeViewer();
	parent.informationPop("Successfully deleted!");
	parent.refresh("menu");
</script>	
END
			}
			
		}
		elsif($item[1] eq 'genome')
		{
		
			my $genomeAsReference = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assembly' AND y = $_");
			$genomeAsReference->execute();
			if($genomeAsReference->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related assemblies using this genome as a reference first!");
</script>	
END
				exit;
			}

			my $assemblyForGenome = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assembly' AND x = $_");
			$assemblyForGenome->execute();
			if ($assemblyForGenome->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related assemblies first!");
</script>	
END
				exit;
			}

			my $deleteSequence=$dbh->do("DELETE FROM matrix WHERE container LIKE 'sequence' AND o = 99 AND x = $_");
			my $deleteSequencePiece=$dbh->do("DELETE FROM matrix WHERE container LIKE 'sequence' AND o = 97 AND x = $_");
			my $deleteAgp=$dbh->do("DELETE FROM matrix WHERE container LIKE 'agp' AND x = $_");
			my $deleteGenome=$dbh->do("DELETE FROM matrix WHERE id = $_");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("general");
</script>	
END
		}
		elsif($item[1] eq 'agp')
		{
		
			my $agpAsReference = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assembly' AND z = $_");
			$agpAsReference->execute();
			if($agpAsReference->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related assemblies using this AGP as a physical reference first!");
</script>	
END
				exit;
			}
			my $deleteAgp=$dbh->do("DELETE FROM matrix WHERE id = $_");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("general");
</script>	
END
		}
		elsif($item[1] eq 'plate')
		{
			if ($item[3] > 0)
			{
				unless($item[9] eq $userName)
				{
					print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("You can NOT delete a label-generated plate unless your created the plate!");
</script>	
END
					exit;
				}
			}

			my $deletePlate=$dbh->do("DELETE FROM matrix WHERE id = $_");
			my $deleteLink=$dbh->do("DELETE FROM link WHERE child = $_ AND type LIKE 'box'");
			my $plateId;
			my $plateInLibrary=$dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'plate' AND z = $item[6] ORDER BY o");
			$plateInLibrary->execute();
			while (my @plateInLibrary = $plateInLibrary->fetchrow_array())
			{
				$plateId->{$plateInLibrary[2]}->{$plateInLibrary[4]} = $plateInLibrary[0];
			}
			my $nofPlates = keys %{$plateId};
			my $updateLibrary=$dbh->do("UPDATE matrix SET o = $nofPlates WHERE id = $item[6]");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
</script>	
END
		}
		elsif($item[1] eq 'pool')
		{
			$libraryId = $item[4];
			my $deletePool=$dbh->do("DELETE FROM matrix WHERE id = $_");
			my $deleteLinkPoolJob=$dbh->do("DELETE FROM link WHERE parent = $_ AND type LIKE 'poolJob'");
			my $deleteLinkPoolClone=$dbh->do("DELETE FROM link WHERE parent = $_ AND type LIKE 'poolClone'");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("viewLibraryTabs$libraryId");
</script>	
END
		}
		elsif($item[1] eq "library")
		{
			my $plateInLibrary = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'plate' AND z = $_");
			$plateInLibrary->execute();
			if ($plateInLibrary->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related plates first!");
</script>	
END
				exit;
			}

			my $rearrayingLibrary = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'library' AND y = $_");
			$rearrayingLibrary->execute();
			if ($rearrayingLibrary->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related rearraying library first!");
</script>	
END
				exit;
			}

			my $fpcForLibrary = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'fpc' AND barcode = $_");
			$fpcForLibrary->execute();
			if ($fpcForLibrary->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related FPC first!");
</script>	
END
				exit;
			}

			my $besForLibrary = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sequence' AND o = 98 AND x = $_");
			$besForLibrary->execute();
			if ($besForLibrary->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related BES first!");
</script>	
END
				exit;
			}

			my $poolForLibrary = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'pool' AND x = $_");
			$poolForLibrary->execute();
			if ($poolForLibrary->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related pools first!");
</script>	
END
				exit;
			}

			my $tagForLibrary = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'tag' AND x = $_");
			$tagForLibrary->execute();
			if ($tagForLibrary->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related tags first!");
</script>	
END
				exit;
			}

			my $assemblyForLibrary = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'assembly' AND x = $_");
			$assemblyForLibrary->execute();
			if ($assemblyForLibrary->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related assemblies first!");
</script>	
END
				exit;
			}

			my $deleteLibrary=$dbh->do("DELETE FROM matrix WHERE id = $_");					
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
</script>	
END
		}
		elsif($item[1] eq "service")
		{
			my $sampleInService = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'sample' AND z = $_");
			$sampleInService->execute();
			if ($sampleInService->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related samples first!");
</script>	
END
				exit;
			}
			my $deleteService=$dbh->do("DELETE FROM matrix WHERE id = $_");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
	parent.refresh("general");
</script>	
END
		}
		elsif($item[1] eq "sample")
		{
			my $paclibForSample = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'paclib' AND z = $_");
			$paclibForSample->execute();
			if ($paclibForSample->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related Paclibs first!");
</script>	
END
				exit;
			}
			my $deleteSample=$dbh->do("DELETE FROM matrix WHERE id = $_");
			my $deleteLink=$dbh->do("DELETE FROM link WHERE child = $_ AND type LIKE 'box'");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
	parent.refresh("general");
</script>	
END
		}
		elsif($item[1] eq "paclib")
		{
			my $smrtcellForPaclib = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'smrtcell' AND o = $_");
			$smrtcellForPaclib->execute();
			if ($smrtcellForPaclib->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related SMRT cells first!");
</script>	
END
				exit;
			}
			my $deletePaclib=$dbh->do("DELETE FROM matrix WHERE id = $_");
			my $deleteLink=$dbh->do("DELETE FROM link WHERE child = $_ AND type LIKE 'box'");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
	parent.refresh("general");
</script>	
END
		}
		elsif($item[1] eq "smrtrun")
		{
			if($item[7] > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("You can NOT delete a $smrtrunStatus{$item[7]} run!");
</script>	
END
				exit;
			}
			else
			{
				my $smrtwellInRun = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE 'smrtwell' AND z = $_");
				$smrtwellInRun->execute();
				if ($smrtwellInRun->rows > 0)
				{
					print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related wells first!");
</script>	
END
					exit;
				}
				my $deleteSmrtrun=$dbh->do("DELETE FROM matrix WHERE id = $_");
			}
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
	parent.refresh("general");
</script>	
END
		}
		elsif($item[1] eq "smrtwell")
		{

			my $smrtrun=$dbh->prepare("SELECT * FROM matrix WHERE id = ?");
			$smrtrun->execute($item[6]);
			my @smrtrun = $smrtrun->fetchrow_array();
			if($smrtrun[7] > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("You can NOT delete the well from a $smrtrunStatus{$smrtrun[7]} run!");
</script>	
END
				exit;
			}
			my $deleteSmrtwell=$dbh->do("DELETE FROM matrix WHERE id = $_");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
	parent.refresh("general");
</script>	
END
		}
		elsif($item[1] eq "vector")
		{
			my $libraryWithVector = $dbh->prepare("SELECT * FROM matrix WHERE container LIKE library AND x = $_");
			$libraryWithVector->execute();
			if ($libraryWithVector->rows > 0)
			{
				print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Please delete related libraries first!");
</script>	
END
					exit;
			}
			my $deleteVector=$dbh->do("DELETE FROM matrix WHERE id = $_");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("general");
</script>	
END
		}
		elsif($item[1] eq 'group')
		{
			my $deleteGroup=$dbh->do("DELETE FROM matrix WHERE id = $_");
			my $deleteLink=$dbh->do("DELETE FROM link WHERE parent = $_ AND type LIKE 'group'");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
</script>	
END
		}
		elsif($item[1] eq 'comment')
		{
			my $deleteComment=$dbh->do("DELETE FROM matrix WHERE id = $_");
			print <<END;
<script>
	parent.closeDialog();
	parent.refresh("menu");
</script>	
END
			exit;
		}
		else
		{
			print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Not a valid deletion!");
</script>	
END
			exit;
		}
	}
	else
	{
		print <<END;
<script>
	parent.closeDialog();
	parent.errorPop("Not a valid user!");
</script>	
END
		exit;
	}
}