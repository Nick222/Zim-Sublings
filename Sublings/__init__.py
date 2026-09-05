# -*- coding: utf-8 -*-
# __version__ = '0.1.0'

import os
import sqlite3
from datetime import datetime

from gi.repository import Gtk

from zim.plugins import PluginClass
from zim.actions import action
from zim.gui.mainwindow import MainWindowExtension


class SublingsPlugin(PluginClass):
    plugin_info = {
        'name': 'Sublings',
        'description': 'Shows sibling pages of the current page.',
        'author': 'Nikolay',
    }


class SublingsMainWindowExtension(MainWindowExtension):

    @action('Сестринские заметки...', menuhints='tools')
    def show_siblings(self):

        main_window = self.window

        # ---------------------------------------------------------
        # 1. Current notebook and page
        # ---------------------------------------------------------

        try:
            notebook = main_window.notebook
            page = main_window.page

        except Exception as e:
            self._show_error(
                'Сестринские заметки',
                'Не удалось получить текущую страницу Zim.\n\n'
                + str(e)
            )
            return

        if page is None:
            self._show_error(
                'Сестринские заметки',
                'Сейчас нет открытой страницы.'
            )
            return

        # ---------------------------------------------------------
        # 2. FilesLayout
        # ---------------------------------------------------------

        try:
            layout = notebook.index.layout

        except Exception as e:
            self._show_error(
                'Сестринские заметки',
                'Не удалось получить FilesLayout Zim.\n\n'
                + str(e)
            )
            return

        # ---------------------------------------------------------
        # 3. Get actual source file of current page
        # ---------------------------------------------------------

        try:
            mapped = layout.map_page(page)
            source_file = mapped[0]

        except Exception as e:
            self._show_error(
                'Сестринские заметки',
                'Не удалось определить файл текущей страницы.\n\n'
                + str(e)
            )
            return

        # ---------------------------------------------------------
        # 4. Convert absolute filesystem path to index path
        # ---------------------------------------------------------

        try:
            root_path = str(layout.root.path)
            source_path = str(source_file.path)

            if not source_path.startswith(root_path):
                raise RuntimeError(
                    'Файл страницы находится вне корня notebook.'
                )

            relative_path = source_path[
                len(root_path):
            ].lstrip('/')

        except Exception as e:
            self._show_error(
                'Сестринские заметки',
                'Не удалось определить путь страницы в индексе Zim.\n\n'
                + str(e)
            )
            return

        # ---------------------------------------------------------
        # 5. Open SQLite index
        # ---------------------------------------------------------

        dbpath = notebook.index.dbpath

        try:
            db = sqlite3.connect(dbpath)
            cursor = db.cursor()

        except Exception as e:
            self._show_error(
                'Сестринские заметки',
                'Не удалось открыть индекс Zim.\n\n'
                'Файл:\n'
                + str(dbpath)
                + '\n\n'
                + str(e)
            )
            return

        try:

            # -----------------------------------------------------
            # 6. Find current page in index
            # -----------------------------------------------------

            cursor.execute(
                """
                SELECT id, parent, path
                FROM files
                WHERE path = ?
                  AND node_type = ?
                """,
                (relative_path, 2)
            )

            current_record = cursor.fetchone()

            if current_record is None:
                self._show_error(
                    'Сестринские заметки',
                    'Текущая страница не найдена в индексе Zim.\n\n'
                    'Page.name:\n'
                    + str(page.name)
                    + '\n\n'
                    'Файловый путь:\n'
                    + str(relative_path)
                    + '\n\n'
                    'Index:\n'
                    + str(dbpath)
                )
                return

            current_id, parent_id, current_db_path = (
                current_record
            )

            # -----------------------------------------------------
            # 7. Find all notes with the same parent
            # -----------------------------------------------------

            cursor.execute(
                """
                SELECT id, path
                FROM files
                WHERE parent = ?
                  AND node_type = ?
                ORDER BY path
                """,
                (parent_id, 2)
            )

            records = cursor.fetchall()

        except Exception as e:

            self._show_error(
                'Сестринские заметки',
                'Ошибка при чтении индекса Zim.\n\n'
                + str(e)
            )
            return

        finally:
            db.close()

        # ---------------------------------------------------------
        # 8. Fallback: current page itself
        # ---------------------------------------------------------

        if not records:
            records = [
                (current_id, current_db_path)
            ]

        # ---------------------------------------------------------
        # 9. Build rows
        # ---------------------------------------------------------

        rows = []

        for record_id, db_path in records:

            try:

                # -------------------------------------------------
                # Convert database filesystem path to Zim Path
                # -------------------------------------------------

                sibling_path = self._path_from_db_path(
                    db_path
                )

                if sibling_path is None:
                    continue

                # -------------------------------------------------
                # Get actual Zim Page
                # -------------------------------------------------

                sibling_page = notebook.get_page(
                    sibling_path
                )

                # -------------------------------------------------
                # Get actual source file
                # -------------------------------------------------

                mapped = layout.map_page(
                    sibling_page
                )

                sibling_file = mapped[0]

                # -------------------------------------------------
                # Modification time
                #
                # IMPORTANT:
                # In Zim 0.77.2 Page.mtime is a Unix timestamp.
                # Use this same numeric value both for display
                # and sorting.
                # -------------------------------------------------

                modified = sibling_page.mtime

                # -------------------------------------------------
                # File size
                # -------------------------------------------------

                try:
                    size = int(
                        sibling_file.size()
                    )

                except Exception:
                    try:
                        size = os.path.getsize(
                            sibling_file.path
                        )

                    except Exception:
                        size = 0

                # -------------------------------------------------
                # Display name
                # -------------------------------------------------

                display_name = sibling_page.basename

                if not display_name:
                    display_name = self._get_display_name(
                        db_path
                    )

                # -------------------------------------------------
                # Add row
                #
                # 0 = displayed name
                # 1 = displayed date
                # 2 = displayed size
                # 3 = logical Zim Path
                # 4 = numeric mtime for sorting
                # 5 = numeric size for sorting
                # 6 = SQLite record ID
                # -------------------------------------------------

                rows.append(
                    (
                        display_name,
                        self._format_mtime(modified),
                        self._format_size(size),
                        sibling_path,
                        float(modified),
                        int(size),
                        int(record_id),
                    )
                )

            except Exception:
                # A single unusual/broken record should not
                # prevent the remaining notes from being shown.
                continue

        # ---------------------------------------------------------
        # 10. Final fallback
        # ---------------------------------------------------------

        if not rows:

            current_mtime = page.mtime

            try:
                current_size = int(
                    source_file.size()
                )

            except Exception:
                try:
                    current_size = os.path.getsize(
                        source_file.path
                    )

                except Exception:
                    current_size = 0

            rows.append(
                (
                    page.basename,
                    self._format_mtime(
                        current_mtime
                    ),
                    self._format_size(
                        current_size
                    ),
                    page,
                    float(current_mtime),
                    int(current_size),
                    int(current_id),
                )
            )

        # ---------------------------------------------------------
        # 11. Show result window
        # ---------------------------------------------------------

        self._show_window(
            main_window,
            rows,
            len(rows)
        )

    # =============================================================
    # Convert database path to Zim Path
    # =============================================================

    @staticmethod
    def _path_from_db_path(db_path):

        if not db_path:
            return None

        # Remove page source extension.
        if db_path.endswith('.txt'):
            db_path = db_path[:-4]

        # Split filesystem path into components.
        parts = db_path.split('/')

        # Zim filesystem representation uses underscores
        # for spaces.
        decoded_parts = []

        for part in parts:
            decoded_parts.append(
                part.replace('_', ' ')
            )

        # Namespace separator in a logical Zim Path is ':'.
        return type(
            'ZimPathHelper',
            (),
            {}
        ) and __import__(
            'zim.notebook',
            fromlist=['Path']
        ).Path(
            ':'.join(decoded_parts)
        )

    # =============================================================
    # Display-name fallback
    # =============================================================

    @staticmethod
    def _get_display_name(path_string):

        if not path_string:
            return ''

        try:
            if path_string.endswith('.txt'):
                path_string = path_string[:-4]

            name = path_string.rsplit('/', 1)[-1]
            return name.replace('_', ' ')

        except Exception:
            return path_string

    # =============================================================
    # Date formatting
    # =============================================================

    @staticmethod
    def _format_mtime(mtime):

        if mtime is None:
            return ''

        try:
            return datetime.fromtimestamp(
                float(mtime)
            ).strftime(
                '%d.%m.%Y %H:%M'
            )

        except Exception:
            return str(mtime)

    # =============================================================
    # Size formatting
    # =============================================================

    @staticmethod
    def _format_size(size):

        if size is None:
            return ''

        try:
            size = int(size)

        except Exception:
            return ''

        if size < 1024:
            return '%d B' % size

        if size < 1024 * 1024:
            return '%.1f KB' % (
                size / 1024.0
            )

        if size < 1024 * 1024 * 1024:
            return '%.1f MB' % (
                size / (1024.0 * 1024.0)
            )

        return '%.1f GB' % (
            size / (1024.0 * 1024.0 * 1024.0)
        )

    # =============================================================
    # Result window
    # =============================================================

    def _show_window(
        self,
        main_window,
        rows,
        count
    ):

        dialog = Gtk.Dialog(
            title='Сестринские заметки',
            transient_for=main_window,
            modal=False
        )

        dialog.set_default_size(
            800,
            450
        )

        # ---------------------------------------------------------
        # Header
        # ---------------------------------------------------------

        label = Gtk.Label()

        label.set_xalign(0.0)

        label.set_markup(
            '<b>Сестринские заметки</b>  (%d)'
            % count
        )

        # ---------------------------------------------------------
        # ListStore
        # ---------------------------------------------------------

        model = Gtk.ListStore(
            str,     # 0 - name
            str,     # 1 - date
            str,     # 2 - size
            object,  # 3 - Zim Path
            float,   # 4 - mtime sort
            int,     # 5 - size sort
            int      # 6 - database id
        )

        for row in rows:
            model.append(row)

        # ---------------------------------------------------------
        # TreeView
        # ---------------------------------------------------------

        tree = Gtk.TreeView(
            model=model
        )

        tree.set_headers_clickable(
            True
        )

        tree.set_enable_search(
            True
        )

        # ---------------------------------------------------------
        # Column: note
        # ---------------------------------------------------------

        renderer_name = (
            Gtk.CellRendererText()
        )

        column_name = Gtk.TreeViewColumn(
            'Заметка',
            renderer_name,
            text=0
        )

        column_name.set_sort_column_id(
            0
        )

        column_name.set_resizable(
            True
        )

        column_name.set_expand(
            True
        )

        tree.append_column(
            column_name
        )

        # ---------------------------------------------------------
        # Column: modification date
        # ---------------------------------------------------------

        renderer_date = (
            Gtk.CellRendererText()
        )

        column_date = Gtk.TreeViewColumn(
            'Изменена',
            renderer_date,
            text=1
        )

        # IMPORTANT:
        # Sort by hidden numeric mtime column,
        # not by displayed date string.
        column_date.set_sort_column_id(
            4
        )

        column_date.set_resizable(
            True
        )

        tree.append_column(
            column_date
        )

        # ---------------------------------------------------------
        # Column: size
        # ---------------------------------------------------------

        renderer_size = (
            Gtk.CellRendererText()
        )

        column_size = Gtk.TreeViewColumn(
            'Размер',
            renderer_size,
            text=2
        )

        # Sort by hidden numeric size column.
        column_size.set_sort_column_id(
            5
        )

        column_size.set_resizable(
            True
        )

        tree.append_column(
            column_size
        )

        # ---------------------------------------------------------
        # Initial sort
        # ---------------------------------------------------------

        model.set_sort_column_id(
            0,
            Gtk.SortType.ASCENDING
        )

        # ---------------------------------------------------------
        # Scrolled window
        # ---------------------------------------------------------

        scrolled = Gtk.ScrolledWindow()

        scrolled.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC
        )

        scrolled.add(
            tree
        )

        # ---------------------------------------------------------
        # Layout
        # ---------------------------------------------------------

        content = (
            dialog.get_content_area()
        )

        content.set_border_width(
            8
        )

        content.pack_start(
            label,
            False,
            False,
            6
        )

        content.pack_start(
            scrolled,
            True,
            True,
            0
        )

        # ---------------------------------------------------------
        # Single-click opening
        # ---------------------------------------------------------

        selection = (
            tree.get_selection()
        )

        selection.connect(
            'changed',
            self._on_selection_changed,
            main_window
        )

        # ---------------------------------------------------------
        # Close button
        # ---------------------------------------------------------

        dialog.add_button(
            'Закрыть',
            Gtk.ResponseType.CLOSE
        )

        dialog.connect(
            'response',
            self._on_dialog_response
        )

        dialog.show_all()

    # =============================================================
    # Single-click handler
    # =============================================================

    def _on_selection_changed(
        self,
        selection,
        main_window
    ):

        model, treeiter = (
            selection.get_selected()
        )

        if treeiter is None:
            return

        try:
            page_path = model.get_value(
                treeiter,
                3
            )

        except Exception:
            return

        if page_path is None:
            return

        try:
            main_window.open_page(
                page_path
            )

        except Exception as e:

            self._show_error(
                'Сестринские заметки',
                'Не удалось открыть страницу.\n\n'
                + str(page_path)
                + '\n\n'
                + str(e)
            )

    # =============================================================
    # Dialog close
    # =============================================================

    @staticmethod
    def _on_dialog_response(
        dialog,
        response_id
    ):

        dialog.destroy()

    # =============================================================
    # Error dialog
    # =============================================================

    def _show_error(
        self,
        title,
        message
    ):

        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )

        dialog.format_secondary_text(
            message
        )

        dialog.run()
        dialog.destroy()
