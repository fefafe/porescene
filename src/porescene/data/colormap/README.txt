porescene bundled colormaps
===========================

Each colormap is a lookup table stored as a plain-text file with 256 rows of
"R G B" values in the interval [0, 1] (see porescene.color.palette.Palette).
Qualitative maps (Set1/Set2/Set3, tab10) are stored as nearest-neighbour blocks
of their discrete colors.

The colormaps are derived from the third-party collections listed below. All of
these licenses are compatible with porescene's GPL-3.0-only license.

Fabio Crameri -- Scientific colour maps
  acton*, bam*, bamako*, batlow*, berlin, bilbao*, broc*, buda*, bukavu, cork*,
  davos*, devon*, fes, glasgow*, grayC*, hawaii*, imola*, lajolla*, lapaz*,
  lipari*, lisbon, managua, navia*, nuuk*, oleron, oslo*, roma*, tofino, tokyo*,
  turku*, vanimo, vik*, ember
  License: MIT -- see LICENSE_cmcrameri.txt

matplotlib perceptually uniform maps
  viridis, plasma, inferno, magma, cividis
  License: CC0 1.0 (public domain) -- see LICENSE_mpl.txt

matplotlib maps
  tab10, cubehelix, twilight
  License: matplotlib (PSF/BSD-style) -- see LICENSE_matplotlib.txt

ColorBrewer qualitative maps
  Set1, Set2, Set3
  License: Apache-2.0 -- see LICENSE_colorbrewer.txt and LICENSE_apache-2.0.txt

Turbo
  turbo
  License: Apache-2.0 -- see LICENSE_turbo.txt and LICENSE_apache-2.0.txt
