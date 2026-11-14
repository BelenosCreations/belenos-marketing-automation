package com.belenos.bam

data class Campaign(val focus: String = "", val facts: String = "", val skipped: Set<Slot> = emptySet()) {
    init {
        require(focus.length <= 160 && facts.length <= 500)
        require(Slot.SAMPLE !in skipped)
    }
}
