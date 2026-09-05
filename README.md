# Sublings — Zim plugin

**Sublings** is a plugin for [Zim Desktop Wiki](https://zim-wiki.org/) that shows the sibling notes of the currently open page.

A *sibling note* is a note that has the same parent page as the current note.

The plugin is useful when you remember approximately **where or when you created a note**, but do not remember its exact name.

## Features

The plugin displays the sibling notes of the current page in a separate window.

The table contains:

- **Note** — note name
- **Modified** — last modification date and time
- **Size** — source file size

All three columns are sortable:

- Note — alphabetically
- Modified — chronologically
- Size — numerically

A **single click** on a note opens that note in Zim.

The current note is included in the list.

If no sibling notes are found, the current note is shown as a fallback.

## Compatibility

Tested with:

- **Zim 0.77.2**
- Linux
- Python 3
- GTK 3 / PyGObject

Other Zim versions may work, but have not been tested.

## Installation

Clone or download this repository.

Copy the `sublings` directory into the Zim user plugin directory:

```text
~/.local/share/zim/plugins/
```

The resulting structure should be:

```text
~/.local/share/zim/plugins/
└── sublings/
    └── __init__.py
```

Restart Zim.

Then enable the plugin in:

```text
Edit → Preferences → Plugins
```

The plugin appears as:

```text
Sublings
```

The command is available under:

```text
Tools → Сестринские заметки...
```

## How it works

Zim maintains an SQLite index for each notebook.

Sublings uses this index to determine:

1. the database record of the current page;
2. its parent ID;
3. all note records having the same parent.

The plugin then uses Zim's `FilesLayout` and page API to obtain the actual page objects and source files.

Modification time is taken from the Zim `Page.mtime` value.

File size is obtained from the page's source file.

This means that the plugin does not maintain a separate database and does not duplicate Zim's page metadata.

## Important technical note

The plugin currently relies on the internal SQLite index used by Zim.

In particular, it uses the `files` table and the following fields:

```text
id
parent
path
node_type
```

For notes, `node_type = 2`.

The SQLite index is an internal implementation detail of Zim. Therefore, changes to Zim's internal index structure in future versions may require changes to this plugin.

The current implementation has been tested against **Zim 0.77.2**.

## Why "Sublings"?

The name is intentionally kept as `Sublings` for compatibility with the current plugin directory and project.

The intended meaning is "sibling notes".

## Status

**Version 0.1.0 — first working release**

The current version is intentionally small and focused on one task:

> Find and quickly open notes located at the same level of the Zim page hierarchy.

Future versions may add additional navigation or search functionality, but the current release deliberately keeps the interface simple.

## License

See [LICENSE](LICENSE).
