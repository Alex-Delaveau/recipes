import {test} from 'node:test'
import assert from 'node:assert/strict'
import {markDurations} from '../../../vue3/src/fork/timers/markup.ts'

test('wraps durations in text, keeps tags', () => {
    const out = markDurations('<p>Cuire <strong>10 min</strong> puis laisser reposer 1 h 30.</p>')
    assert.equal(out, '<p>Cuire <strong><span class="fork-timer-link" role="button" tabindex="0" data-seconds="600">10 min</span></strong> puis laisser reposer <span class="fork-timer-link" role="button" tabindex="0" data-seconds="5400">1 h 30</span>.</p>')
})
test('ranges carry their upper bound', () => {
    assert.match(markDurations('<p>Enfourner 20 à 25 minutes.</p>'), /data-seconds="1200" data-max="1500">20 à 25 minutes</)
})
test('entities are decoded for detection and text stays escaped', () => {
    const out = markDurations('<p>Un quart d&#39;heure &amp; 5&nbsp;min &lt;b&gt;</p>')
    assert.match(out, /data-seconds="900">Un quart d'heure</)
    assert.match(out, /data-seconds="300">5 min</)
    assert.match(out, /&amp; .*&lt;b&gt;/)
})
test('braces are escaped so the template compiler never sees an expression', () => {
    const out = markDurations('<p>&#123;&#123; alert(1) &#125;&#125; cuire 5 min</p>')
    assert.ok(!out.includes('{{'))
})
test('scaled numbers and links are left alone', () => {
    const html = '<p><scalable-number v-bind:number="10" v-bind:factor="ingredient_factor"></scalable-number> min <a href="/x">2 min</a></p>'
    assert.equal(markDurations(html), html)
})
test('no duration: unchanged', () => {
    const html = '<p>Préchauffer le four à 180 °C. Pour 4 personnes.</p>'
    assert.equal(markDurations(html), html)
})
