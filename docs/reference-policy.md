# Reference policy

The community edition of CISO Assistant (`intuitem/ciso-assistant-community`) inspired this project. Its code outside the `enterprise` directory is under the AGPL v3. Its `enterprise` directory is under a commercial licence.

## What was done

The reference repository was read to learn which features exist and how its data relates: the folder tree, role assignment per folder, framework libraries as data, and mappings between frameworks. Only the structure, the dependency list and the public feature list were studied.

## Rules for this project

1. No source code, schema file, template, translation, or user-interface wording is copied or closely paraphrased from the reference project.
2. Nothing from its `enterprise` directory is read for implementation purposes.
3. Names, tables, API shapes and screens here come from this project's own design (see `ARCHITECTURE.md`).
4. Framework content is taken from the standards bodies' own publications, under the licence each one states. The source and licence of every framework file are recorded next to it. Standards sold under copyright, such as the ISO 27000 family, are not bundled. Users can enter their own copy.
5. When a feature needs a closer look at the reference project, the review goes into a short written description first, and the code is written from that description.

## Why

Copying AGPL code would place this project under the AGPL. The commercial directory carries a licence that forbids use without a contract. Working from descriptions keeps the licence of this repository a free choice, which is for you to make. This is practical guidance, not legal advice.
