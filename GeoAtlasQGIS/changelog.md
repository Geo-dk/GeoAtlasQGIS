# Changelog

## Version 1.3.1

- Kommatal værdi på Slice tool levels
- Vælger automatisk model med højest prioritet når man laver ny virtuel boring, crosssection profil eller slice tool.
- Husker valgt model, og prøver at anvende den hvis man laver ny boring eller crosssection profil og samme model eksisterer igen (Husker kun den forrige)
- Viser nu korrekt model som valgt i dropdown når man laver en virtuel boring, crosssection profil eller slice tool.
- Den automatisk valgte model gøres nu med modellens form fra WFS servicen, frem for en omringende firkant (Forbedret præcision ved ny boring / slice tool, feks Jylland model præsenterer ikke sig selv længere på Fyn)
- Viser kun modeller i dropdown som indeholder data (virtuel boringer der har data på punktet, slice tool checker midten af kort-viewet
  - Crosssection profil bruger stadig en models omkringede firkant da den kan overlappe en model, hvor man gerne vil se data fra. (Et punkt fra profilen skal dog være inde for modellens omringede firkant, før den bliver vist)
- Optimeringer i forskellige tools så de kører hurtigere
- Pop up til nogle fejlbeskeder (HTML Error 400)
- Forbedret GeoAtlasReport (dem der kommer når man trykker Make Layout på en crosssection profil)
- Fikset forskellige fejl, bemærkelsesværdige:
  - Fikset fejl i udregning af vinkel af lodrette og vandrette linjer hvis hældningen var 0 grader
  - Fikset et problem som opstod når man lavede en ny crosssection ud fra QGIS line tool uden at have lavet en med GeoAtlasQGIS plugin først
- Opdateret til at bruge geo's v3 api og ny geomodel api, samt mapv2
- Skulle gerne virke ordentligt på andre operativsystemer
- Rengjort koden en del
- Forskellige andre små bug fixes, forbedringer og optimeringer
