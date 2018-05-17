# [Pangu LIMS Docs](README.md)
## Genome Puzzle Master Manual
- [GPM Workflow](#gpm-workflow)
- [GPM assemblyRun](#gpm-assemblyrun)
- [Visualization of typical available data in GPM](#visualization-of-typical-available-data-in-gpm)
- [Flowchart for processing unitigs with postHGAP](#flowchart-for-processing-unitigs-with-posthgap)
- [GPM Basic User Guide](GPM-Userguide.md)

### GPM Workflow
- Upload Subject and Reference Genomes.
- Run preliminary alignments of each subject Genome to the Reference.
- Run an assembly of each Genome.
- “Clean Up” each Chromosome for the assemblies.
- Fill any possible gaps using alternative assemblies of the same subject.  
- Eliminate any identifiable contamination.  

### GPM assemblyRun
- AssemblyRun operations
![assemblyRun](images/assemblyRun-04-01-JZ.png)

- Screenshot of assemblyRun interface
![assemblyRun-interface](images/assemblyRun.png)

### Visualization of typical available data in GPM
- GPM assemblyCtg view of a 500-KB region

> ![ctgViewer](images/ctgViewer.png)
> AssemblySeqs, top and bottom, are shown as overlapping (yellow) and fully redundant assemblySeqs are gray. The retained (green) and removed (gray) portions of assemblySeqs are indicated.

- Chromosome-scale view of a 500-KB region that compares two genome assemblies to a Reference sequence

> ![chrViewer](images/chrViewer.png)
> The Reference Sequence is shown in the middle (bright green) with alignments (yellow) to each assemblyCtg (violet) at the top and bottom. The assemblyCtg order can be changed by drag-and-drop.

### Flowchart for processing unitigs with postHGAP
![postHGAP](images/postHGAP-4-JZ.png)

### [GPM Basic User Guide](GPM-Userguide.md)