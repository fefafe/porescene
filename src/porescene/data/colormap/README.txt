porescene bundled colormaps
===========================

Each colormap is a lookup table stored as a plain-text file with 256 rows of
"R G B" values in the interval [0, 1] (see porescene.color.palette.Palette).
Qualitative maps (Set1/Set2/Set3, Accent, Dark2, Paired, Pastel1/Pastel2) are
stored as nearest-neighbour blocks of their discrete colors; tab10 is stored as
its 10 discrete colors.

The colormaps are derived from the third-party collections listed below. All of
these licenses are compatible with porescene's GPL-3.0-only license.

Fabio Crameri -- Scientific colour maps
  acton*, bam*, bamako*, batlow*, berlin, bilbao*, broc*, buda*, bukavu, cork*,
  davos*, devon*, fes, glasgow*, grayC*, hawaii*, imola*, lajolla*, lapaz*,
  lipari*, lisbon, managua, navia*, nuuk*, oleron, oslo*, roma*, tofino, tokyo*,
  turku*, vanimo, vik*, ember
  License: MIT -- see LICENSE_cmcrameri.txt

cmocean -- Kristen M. Thyng
  thermal, haline, solar, ice, gray, oxy, deep, dense, algae, matter, turbid,
  speed, amp, tempo, rain, phase, topo, balance, delta, curl, diff, tarn
  License: MIT -- see LICENSE_cmocean.txt

colorcet -- Peter Kovesi (perceptually uniform maps)
  bgy, bgyw, bjy, bkr, bky, bmw, bmy, bwy, colorwheel, coolwarm, cwr, dimgray,
  fire, gouldian, gwv, isolum, kb, kbc, kbgyw, kg, kgy, kr, rainbow, rainbow4
  License: CC-BY 4.0 -- see LICENSE_colorcet.txt

matplotlib perceptually uniform maps
  viridis, plasma, inferno, magma, cividis
  License: CC0 1.0 (public domain) -- see LICENSE_mpl.txt

matplotlib maps
  tab10, cubehelix, twilight
  License: matplotlib (PSF/BSD-style) -- see LICENSE_matplotlib.txt

ColorBrewer -- Cynthia A. Brewer
  Sequential:  Blues, BuGn, BuPu, GnBu, Greens, Greys, Oranges, OrRd, PuBu,
               PuBuGn, PuRd, Purples, RdPu, Reds, YlGn, YlGnBu, YlOrBr, YlOrRd
  Diverging:   BrBG, PiYG, PRGn, PuOr, RdBu, RdGy, RdYlBu, RdYlGn, Spectral
  Qualitative: Set1, Set2, Set3, Accent, Dark2, Paired, Pastel1, Pastel2
  License: Apache-2.0 -- see LICENSE_colorbrewer.txt and LICENSE_apache-2.0.txt

Turbo
  turbo
  License: Apache-2.0 -- see LICENSE_turbo.txt and LICENSE_apache-2.0.txt
