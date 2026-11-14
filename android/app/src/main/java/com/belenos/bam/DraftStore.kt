package com.belenos.bam

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.time.LocalDate

data class Draft(val day: LocalDate, val slot: Slot, val caption: String)

class DraftStore(context: Context) : SQLiteOpenHelper(context, "drafts.db", null, 1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE draft (
            day TEXT NOT NULL, slot TEXT NOT NULL, caption TEXT NOT NULL,
            PRIMARY KEY (day, slot)
        )""")
    }

    override fun onUpgrade(db: SQLiteDatabase, old: Int, new: Int) = Unit

    fun contains(day: LocalDate, slot: Slot): Boolean =
        readableDatabase.rawQuery("SELECT 1 FROM draft WHERE day=? AND slot=?",
            arrayOf(day.toString(), slot.name)).use { it.moveToFirst() }

    fun recent(limit: Int = 60): List<Draft> =
        readableDatabase.rawQuery(
            "SELECT day, slot, caption FROM draft ORDER BY day DESC, rowid DESC LIMIT ?",
            arrayOf(limit.toString())
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(Draft(LocalDate.parse(cursor.getString(0)), Slot.valueOf(cursor.getString(1)),
                        cursor.getString(2)))
                }
            }
        }

    fun save(draft: Draft, replace: Boolean) {
        val values = ContentValues().apply {
            put("day", draft.day.toString())
            put("slot", draft.slot.name)
            put("caption", draft.caption)
        }
        writableDatabase.insertWithOnConflict("draft", null, values,
            if (replace) SQLiteDatabase.CONFLICT_REPLACE else SQLiteDatabase.CONFLICT_IGNORE)
    }
}
