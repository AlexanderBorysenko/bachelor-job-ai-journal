<script setup lang="ts">
import { ref } from "vue";
import type { TimelineGroup } from "../../composables/useStoryPoints";
import { useI18n } from "vue-i18n";
import { bcp47, type Language } from "../../i18n";

defineProps<{ groups: TimelineGroup[]; activeDate: string | null }>();
const emit = defineEmits<{ (e: "navigate", date: string): void }>();
const { locale } = useI18n();

const scroller = ref<HTMLElement | null>(null);
function scrollRail(delta: number) {
    scroller.value?.scrollBy({ top: delta, behavior: "smooth" });
}
function fmt(date: string) {
    return new Date(date + "T00:00:00").toLocaleDateString(
        bcp47(locale.value as Language),
        {
            day: "numeric",
            month: "short",
        },
    );
}
</script>

<template>
    <div class="flex flex-col">
        <div ref="scroller" class="overflow-y-auto max-h-[60vh] pr-1">
            <div class="relative">
                <!-- continuous vertical line -->
                <div
                    class="absolute top-2 bottom-2 left-18 w-px bg-sand-200"
                    aria-hidden="true"
                ></div>
                <ul class="space-y-6">
                    <li v-for="g in groups" :key="g.date">
                        <button
                            type="button"
                            @click="emit('navigate', g.date)"
                            class="group/item relative grid w-full grid-cols-[4.5rem_1fr] items-start gap-4 rounded-lg py-1.5 text-left cursor-pointer transition-colors hover:bg-sand-50"
                        >
                            <!-- date: left of the line, dimmed (secondary) -->
                            <span
                                class="pr-3 pt-0.5 text-right text-xs tabular-nums transition-colors"
                                :class="
                                    g.date === activeDate
                                        ? 'text-accent font-medium'
                                        : 'text-sand-400 group-hover/item:text-sand-500'
                                "
                                >{{ fmt(g.date) }}</span
                            >
                            <!-- decorative dot sitting on the line -->
                            <span
                                class="absolute left-18 top-2 h-2.5 w-2.5 -translate-x-1/2 rounded-full ring-4 ring-white transition-colors"
                                :class="
                                    g.date === activeDate
                                        ? 'bg-accent'
                                        : 'bg-sand-300 group-hover/item:bg-accent/60'
                                "
                                aria-hidden="true"
                            ></span>
                            <!-- titles: right of the line, primary (readable, full text) -->
                            <ul class="space-y-1">
                                <li
                                    v-for="p in g.points"
                                    :key="p.id"
                                    class="text-sm leading-snug transition-colors"
                                    :class="
                                        g.date === activeDate
                                            ? 'text-accent font-medium'
                                            : 'text-sand-800 group-hover/item:text-accent'
                                    "
                                >
                                    {{ p.title }}
                                </li>
                            </ul>
                        </button>
                    </li>
                </ul>
            </div>
        </div>
        <div class="flex justify-center gap-2 mt-2">
            <button
                class="px-2 py-1 text-sand-500 hover:text-accent"
                @click="scrollRail(-120)"
                aria-label="up"
            >
                ▲
            </button>
            <button
                class="px-2 py-1 text-sand-500 hover:text-accent"
                @click="scrollRail(120)"
                aria-label="down"
            >
                ▼
            </button>
        </div>
    </div>
</template>
