# Vlastní instalace a příspěvky autorovi

main v tomto forku obsahuje společnou testovanou verzi pro domácí HA. Repozitář aplikací v HA je https://github.com/littlecake/energywizard . Doplněk se sestavuje ze zdrojů tohoto forku, neposkytuje veřejné porty a vynucuje SHADOW_MODE=true.

feat/czech-translation je samostatná větev se dvěma soubory překladu. feat/czech-ote-hdo-tariffs obsahuje samostatné rozšíření tarifů bez nastavení domácí instalace. Tyto větve jsou založené přímo na upstream/main, aby PR neobsahovaly naše změny Dockerfile, repository.yaml a konfigurace doplňku.

Aktualizace od autora: načíst murre87/energywizard jako git remote upstream, provést fetch upstream a merge upstream/main do main našeho forku. Vyřešit konflikty, spustit cílené i upstream testy a zvýšit verzi doplňku. Teprve potom aktualizovat HA. Nepoužívat reset --hard ani GitHub Discard commits, protože by smazaly naše vlastní úpravy.

Automatické přebírání a nasazování autorových změn není zapnuté. Fork umožňuje standardní GitHub PR proti autorovu main. Přes konektor zatím založení PR selhalo chybou 403 Resource not accessible by integration; větve a commity byly uloženy.
