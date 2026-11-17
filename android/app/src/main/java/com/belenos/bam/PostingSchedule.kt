package com.belenos.bam

import android.content.SharedPreferences
import java.time.DayOfWeek
import java.time.LocalTime

data class PostingRule(val time: LocalTime, val days: Set<DayOfWeek>)

internal val postingSlots = listOf(Slot.MORNING, Slot.OPENING, Slot.EVENING)

class PostingSchedule private constructor(private val rules: Map<Slot, PostingRule>) {
    operator fun get(slot: Slot): PostingRule = rules.getValue(slot)

    companion object {
        private val defaults = mapOf(
            Slot.MORNING to PostingRule(checkNotNull(Slot.MORNING.draftTime), DayOfWeek.entries.toSet()),
            Slot.OPENING to PostingRule(checkNotNull(Slot.OPENING.draftTime),
                setOf(DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY)),
            Slot.EVENING to PostingRule(checkNotNull(Slot.EVENING.draftTime),
                setOf(DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY))
        )
        val DEFAULT = PostingSchedule(defaults)

        internal fun eligibleDays(slot: Slot): Set<DayOfWeek> =
            if (slot == Slot.OPENING) defaults.getValue(slot).days else DayOfWeek.entries.toSet()

        internal fun read(preferences: SharedPreferences): PostingSchedule {
            val values = preferences.all
            return PostingSchedule(defaults.mapValues { (slot, fallback) ->
                val stored = values[key(slot)] as? String
                decode(slot, stored) ?: fallback
            })
        }

        internal fun save(preferences: SharedPreferences, slot: Slot, rule: PostingRule) {
            require(valid(slot, rule))
            val days = rule.days.sortedBy(DayOfWeek::getValue).joinToString(",") { it.value.toString() }
            preferences.edit().putString(key(slot), "${rule.time}|$days").apply()
        }

        private fun decode(slot: Slot, stored: String?): PostingRule? {
            if (stored == null) return null
            return runCatching {
                val fields = stored.split('|')
                require(fields.size == 2)
                val days = fields[1].split(',').filter { it.isNotEmpty() }
                    .map { DayOfWeek.of(it.toInt()) }.toSet()
                PostingRule(LocalTime.parse(fields[0]), days).also { require(valid(slot, it)) }
            }.getOrNull()
        }

        internal fun valid(slot: Slot, rule: PostingRule): Boolean =
            slot in postingSlots && rule.time.second == 0 && rule.time.nano == 0 &&
                eligibleDays(slot).containsAll(rule.days) && (slot != Slot.OPENING || rule.time < LocalTime.NOON)

        private fun key(slot: Slot) = "posting_rule_${slot.name.lowercase()}"
    }
}
