import sqlite3
import re

from functools import partial

from tkinter import Tk, Toplevel
from tkinter import Frame, Menu, Button, Text, Scrollbar
from tkinter import N, W, E, S, NO, YES, BOTH
from tkinter import filedialog
from tkinter.ttk import Notebook, Treeview

class SQLQueryWindow(Toplevel):
    def __init__(self, *args, db, query_tab, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db
        self.query_tab = query_tab
        self.geometry('800x400+810+10')
        self.title('Query')
        self.create_menu()
        self.create_widgets()
        self.focus_force()
    
    def create_menu(self):
        self._menu = Menu(self)
        self.config(menu=self._menu)

        self.run_query_menu = Menu(self._menu)
        self._menu.add_command(label='Run', command=self.run_query)
        self._menu.add_command(label='Close', command=self.destroy)

    def create_widgets(self):
        # Top Level Frame:
        self.frame = Frame(self)
        self.frame.pack(expand=YES, fill=BOTH)
        self.query_input = Text(self.frame)
        self.query_input.pack(expand=YES, fill=BOTH)
        self.query_input.insert(1.0, 'SELECT * FROM summoners')

    def run_query(self):
        fields, results = self.db.query(self.query_input.get(1.0, 'end'))
        self.query_tab.fill_values(fields, results)

class SQLTableFrame(Frame):
    def __init__(self, parent, table_name, db):
        super().__init__(parent)
        self.table_name = table_name
        self.db = db
        self.grid()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.create_widgets()

    def create_widgets(self):
        table_fields = tuple(self.db._tables[self.table_name]['fields'])
        data = self.db.read_table(self.table_name, table_fields)

        self.tree = Treeview(self, selectmode="extended", columns=table_fields)
        if len(data) >= 16:
            self.tree_scrollbar = Scrollbar(self, orient='vertical', command=self.tree.yview)
            self.tree_scrollbar.pack(side='right', fill='y')
            self.tree.configure(yscrollcommand=self.tree_scrollbar.set)
        self.tree.pack(expand=YES, fill=BOTH)

        self.tree.heading('#0', text='id')
        self.tree.column('#0', minwidth=40, width=40, stretch=NO)
        for idx, field in enumerate(table_fields):
            self.tree.heading(f'#{idx+1}', text=field)
            self.tree.column(f'#{idx+1}', minwidth=40, width=560//len(table_fields), stretch=YES)

        # tree.insert(parent -root if empty-, index -0-9 or end, iid -???, text -first, values -[1:])
        for idx, value in enumerate(data):
            self.tree.insert('', index='end', text=idx+1, values=value[:])

class SQLTableFrameQuery(Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack()
    
    def fill_values(self, fields, results):
        if hasattr(self, 'tree'):
            self.tree.pack_forget()
            self.tree.destroy()
        if hasattr(self, 'tree_scrollbar'):
            self.tree_scrollbar.destroy()
            del self.tree_scrollbar

        self.tree = Treeview(self, selectmode='extended', columns=fields)
        if len(results) >= 16 and not hasattr(self, 'tree_scrollbar'):
            self.tree_scrollbar = Scrollbar(self, orient='vertical', command=self.tree.yview)
            self.tree_scrollbar.pack(side='right', fill='y')
            self.tree.configure(yscrollcommand=self.tree_scrollbar.set)

        for idx, field in enumerate(fields):
            self.tree.heading(f'#{idx}', text=field)
            self.tree.column(f'#{idx}', minwidth=40, width=560//len(fields))
        
        for idx, value in enumerate(results):
            try:
                self.tree.insert('', index='end', text=str(value[0]), values=value[1:])
            except:
                print('Error with:', idx, value)

        self.tree.pack(expand=YES, fill=BOTH)

class SQLiteConnector:
    def __init__(self, db_location):
        self.db_location = db_location
        self._tables = {}
        self._read_master_table()
    
    @property
    def tables(self):
        return self._tables.keys()

    def _read_master_table(self):
        with self as cur:
            cur.execute('SELECT * FROM sqlite_master')
            tables = cur.fetchall()
            self._parse_tables(tables)
    
    def _parse_tables(self, tables):
        re_table_fields = re.compile('([0-9a-z\_]+)\s[0-9a-z\_]+')
        re_view_fields = re.compile('[a-zA-Z\.\(\)]+ as ([a-zA-Z]+)')
        for table in tables:
            if table[4].startswith('CREATE TABLE'):
                self._tables[table[1]] = {
                    'type': 'TABLE',
                    'fields': [field for field in re_table_fields.findall(table[4])]
                }
            elif table[4].startswith('CREATE VIEW'):
                self._tables[table[1]] = {
                    'type': 'VIEW',
                    'fields': [field for field in re_view_fields.findall(table[4])]
                }

    def read_table(self, table_name, fields):
        with self as cur:
            cur.execute(f"SELECT {','.join(fields)} FROM {table_name} ORDER BY rowid")
            table_info = cur.fetchall()
            return table_info

    def query(self, query):
        with self as cur:
            cur.execute(query.replace('\n', ' '))
            if query.startswith('INSERT INTO'):
                fields = ('Items Added', )
                results = ((cur.rowcount, ), )
                self.t_connection.commit()
            elif query.startswith('DELETE FROM'):
                fields = ('Items Deleted', )
                results = ((cur.rowcount, ), )
                self.t_connection.commit()
            elif query.startswith('DROP VIEW'):
                fields = ('View deleted', )
                results = (('Complete'), )
                self.t_connection.commit()
            elif query.startswith('DROP TABLE'):
                fields = ('Table dropped', )
                results = (('Complete'), )
                self.t_connection.commit()
            else:
                fields = [f[0] for f in cur.description]
                results = cur.fetchall()
        return fields, results

    def __enter__(self):
        self.t_connection = sqlite3.connect(self.db_location)
        self.t_cursor = self.t_connection.cursor()
        return self.t_cursor
    
    def __exit__(self, type, value, traceback):
        self.t_cursor.close()
        self.t_connection.close()
        return

class SQLiteReader(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.option_add('*tearOff', False)
        self.master.title('SQLite Reader')
        self.master.geometry('800x400+10+10')
        self.grid(column=0, row=0, sticky=(N, W, E, S))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.create_menu()
        self.create_widget()
        self.tabs = []

    def create_widget(self):
        self.tab_parent = Notebook(self)
        self.tab_parent.grid(column=0, row=0, sticky=(N, W, S, E))

    def create_menu(self):
        self._menu = Menu(self.master)
        self.master.config(menu=self._menu)

        self.file_menu = Menu(self._menu)
        self.file_menu.add_command(label='Open', command=self.open_database)
        self.file_menu.add_command(label='Query', command=self.run_query, state='disabled')

        self._menu.add_cascade(label='File', menu=self.file_menu)
        self._menu.add_command(label='Reload', command=self.reload_current_table, state='disabled')
        self._menu.add_command(label='Exit', command=self.master.destroy)

    def open_database(self, new_folder=True):
        for item in self.tab_parent.winfo_children():
            item.destroy()
        if new_folder:
            self.file_name = filedialog.askopenfilename()

        self.db = SQLiteConnector(self.file_name)
        for idx, table in enumerate(self.db.tables):
            new_tab = SQLTableFrame(self.tab_parent, table, self.db)
            self.tab_parent.add(new_tab, text=table)

        self.tab_query = SQLTableFrameQuery(self.tab_parent)
        self.tab_parent.add(self.tab_query, text='queries')

        self._menu.entryconfig('Reload', state='normal')
        self.file_menu.entryconfig('Query', state='normal')

    def reload_current_table(self):
        if hasattr(self, 'query_window'):
            self.query_window.destroy()
        self.open_database(new_folder=False)

    def run_query(self):
        self.tab_parent.select(self.tab_query)
        self.query_window = SQLQueryWindow(self.master, db=self.db, query_tab=self.tab_query)

def main():
    root = Tk()
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    app = SQLiteReader(master=root)
    app.mainloop()

if __name__ == '__main__':
    main()
