package com.belenos.bam

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.time.Instant
import java.time.LocalDate

class DraftStore(context: Context) : SQLiteOpenHelper(context, "drafts.db", null, 3) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE draft (
            day TEXT NOT NULL, slot TEXT NOT NULL, caption TEXT NOT NULL,
            saved_at INTEGER, origin TEXT,
            PRIMARY KEY (day, slot)
        )""")
        createCampaigns(db)
    }

    override fun onUpgrade(db: SQLiteDatabase, old: Int, new: Int) {
        if (old < 2) createCampaigns(db)
        if (old < 3) {
            db.execSQL("ALTER TABLE draft ADD COLUMN saved_at INTEGER")
            db.execSQL("ALTER TABLE draft ADD COLUMN origin TEXT")
        }
    }

    private fun createCampaigns(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE campaign (
            day TEXT PRIMARY KEY NOT NULL, focus TEXT NOT NULL,
            facts TEXT NOT NULL, skipped TEXT NOT NULL
        )""")
    }

    fun campaign(day: LocalDate): Campaign =
        readableDatabase.rawQuery("SELECT focus, facts, skipped FROM campaign WHERE day=?",
            arrayOf(day.toString())).use { cursor ->
            if (!cursor.moveToFirst()) Campaign() else Campaign(
                cursor.getString(0), cursor.getString(1),
                cursor.getString(2).split(",").filter { it.isNotEmpty() }.map(Slot::valueOf).toSet()
            )
        }

    fun saveCampaign(day: LocalDate, campaign: Campaign) {
        val values = ContentValues().apply {
            put("day", day.toString())
            put("focus", campaign.focus)
            put("facts", campaign.facts)
            put("skipped", campaign.skipped.joinToString(",") { it.name })
        }
        check(writableDatabase.replaceOrThrow("campaign", null, values) != -1L)
    }

    fun edit(draft: Draft, caption: String): Boolean {
        val values = ContentValues().apply { put("caption", caption) }
        val timing = draft.timing
        val where = "day=? AND slot=? AND caption=?"
        val args = arrayOf(draft.day.toString(), draft.slot.name, draft.caption)
        return if (timing == null) {
            writableDatabase.update("draft", values, "$where AND saved_at IS NULL", args) == 1
        } else {
            writableDatabase.update("draft", values, "$where AND saved_at=? AND origin=?",
                args + arrayOf(timing.savedAt.toEpochMilli().toString(), timing.origin.name)) == 1
        }
    }

    fun contains(day: LocalDate, slot: Slot): Boolean =
        readableDatabase.rawQuery("SELECT 1 FROM draft WHERE day=? AND slot=?",
            arrayOf(day.toString(), slot.name)).use { it.moveToFirst() }

    fun recent(limit: Int = 60): List<Draft> =
        readableDatabase.rawQuery(
            "SELECT day, slot, caption, saved_at, origin FROM draft ORDER BY day DESC, rowid DESC LIMIT ?",
            arrayOf(limit.toString())
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    val timing = if (cursor.isNull(3) || cursor.isNull(4)) null else
                        DraftTiming(Instant.ofEpochMilli(cursor.getLong(3)), DraftOrigin.valueOf(cursor.getString(4)))
                    add(Draft(LocalDate.parse(cursor.getString(0)), Slot.valueOf(cursor.getString(1)),
                        cursor.getString(2), timing))
                }
            }
        }

    fun saveGenerated(draft: Draft, plannedCampaign: Campaign): Boolean {
        val db = writableDatabase
        db.beginTransaction()
        try {
            if (campaign(draft.day) != plannedCampaign) return false
            val timing = checkNotNull(draft.timing)
            val values = ContentValues().apply {
                put("day", draft.day.toString())
                put("slot", draft.slot.name)
                put("caption", draft.caption)
                put("saved_at", timing.savedAt.toEpochMilli())
                put("origin", timing.origin.name)
            }
            db.insertWithOnConflict("draft", null, values,
                if (draft.slot == Slot.SAMPLE) SQLiteDatabase.CONFLICT_REPLACE
                else SQLiteDatabase.CONFLICT_IGNORE)
            db.setTransactionSuccessful()
            return true
        } finally {
            db.endTransaction()
        }
    }
}
