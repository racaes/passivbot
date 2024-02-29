#!/bin/bash

# Change to the directory containing the Python script
cd /home/tdb/git/passivbot/

git remote -v | grep -w upstream || git remote add upstream https://github.com/enarjord/passivbot.git
git remote set-url upstream https://github.com/enarjord/passivbot.git

# Extrae las ramas y sus respectivas confirmaciones desde el repositorio ascendente. 
# Las confirmaciones en BRANCHNAME se almacenarán en la rama local upstream/BRANCHNAME.
# Donde upstream --> https://github.com/enarjord/passivbot.git
git fetch upstream

# Revise la rama predeterminada local de la bifurcación; en este caso, utilizamos master.
git checkout master

git pull

# Combine los cambios de la rama predeterminada ascendente (en este caso, upstream/main) 
# en la rama predeterminada local. Esto hace que la rama predeterminada de tu bifurcación se 
# sincronice con el repositorio ascendente sin perder tus cambios locales.
git merge upstream/master

git push

git checkout dev

git pull

# git merge --no-ff origin/master
git merge origin/master

git push