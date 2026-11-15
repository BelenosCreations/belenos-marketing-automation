package com.belenos.bam

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.time.Instant
import java.time.LocalDate

enum class DraftQueue(val predicate: String) {
    CONTENT_NEEDED("slot != 'SAMPLE' AND content_needed != ''"),
    NEEDS_APPROVAL("slot != 'SAMPLE' AND content_needed = '' AND approved = 0")
}

class DraftStore(context: Context) : SQLiteOpenHelper(context, "drafts.db", null, 4) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE draft (
            day TEXT NOT NULL, slot TEXT NOT NULL, caption TEXT NOT NULL,
            saved_at INTEGER, origin TEXT,
            content_needed TEXT NOT NULL DEFAULT '', image_prompt TEXT NOT NULL DEFAULT '',
            approved INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 0,
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
        if (old < 4) {
            db.execSQL("ALTER TABLE draft ADD COLUMN content_needed TEXT NOT NULL DEFAULT ''")
            db.execSQL("ALTER TABLE draft ADD COLUMN image_prompt TEXT NOT NULL DEFAULT ''")
            db.execSQL("ALTER TABLE draft ADD COLUMN approved INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE draft ADD COLUMN revision INTEGER NOT NULL DEFAULT 0")
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
        return update(draft, ContentValues().apply {
            put("caption", caption)
            if (caption != draft.caption) put("approved", 0)
        })
    }

    fun setContentNeeded(draft: Draft, note: String): Boolean {
        if (draft.slot == Slot.SAMPLE) return false
        val normalized = note.trim()
        return update(draft, ContentValues().apply {
            put("content_needed", normalized)
            if (normalized != draft.review.contentNeeded) put("approved", 0)
        })
    }

    fun setImagePrompt(draft: Draft, prompt: String): Boolean {
        return update(draft, ContentValues().apply { put("image_prompt", prompt.trim()) })
    }

    fun setApproval(draft: Draft, approved: Boolean): Boolean {
        if (draft.slot == Slot.SAMPLE || (approved && draft.review.contentNeeded.isNotEmpty())) return false
        return update(draft, ContentValues().apply { put("approved", if (approved) 1 else 0) },
            requireContentReady = approved)
    }

    private fun update(draft: Draft, values: ContentValues, requireContentReady: Boolean = false): Boolean {
        val timing = draft.timing
        val where = "day=? AND slot=? AND caption=? AND revision=?" +
            if (requireContentReady) " AND content_needed = ''" else ""
        val args = arrayOf(draft.day.toString(), draft.slot.name, draft.caption, draft.review.revision.toString())
        values.put("revision", draft.review.revision + 1)
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

    fun count(queue: DraftQueue): Int =
        readableDatabase.rawQuery("SELECT COUNT(*) FROM draft WHERE ${queue.predicate}", null)
            .use { cursor ->
                cursor.moveToFirst()
                cursor.getInt(0)
            }

    fun canCopyCaption(draft: Draft): Boolean {
        if (draft.slot == Slot.SAMPLE) return true
        return readableDatabase.rawQuery("""SELECT 1 FROM draft WHERE day=? AND slot=?
            AND revision=? AND caption=? AND approved=1 AND content_needed=''""",
            arrayOf(draft.day.toString(), draft.slot.name, draft.review.revision.toString(), draft.caption)
        ).use { it.moveToFirst() }
    }

    fun recent(limit: Int = 60, queue: DraftQueue? = null): List<Draft> =
        readableDatabase.rawQuery(
            "SELECT day, slot, caption, saved_at, origin, content_needed, image_prompt, approved, revision " +
                "FROM draft WHERE ${queue?.predicate ?: "1"} ORDER BY day DESC, rowid DESC LIMIT ?",
            arrayOf(limit.toString())
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    val timing = if (cursor.isNull(3) || cursor.isNull(4)) null else
                        DraftTiming(Instant.ofEpochMilli(cursor.getLong(3)), DraftOrigin.valueOf(cursor.getString(4)))
                    add(Draft(LocalDate.parse(cursor.getString(0)), Slot.valueOf(cursor.getString(1)),
                        cursor.getString(2), timing, DraftReview(cursor.getString(5), cursor.getString(6),
                            cursor.getInt(7) != 0, cursor.getLong(8))))
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
