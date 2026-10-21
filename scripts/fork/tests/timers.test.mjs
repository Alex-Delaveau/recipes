// Unit tests for the fork's pure front-end helpers, run by scripts/fork/verify.sh with `node --test`
// (node >= 22.18 strips TypeScript types, so the .ts sources are imported as they are).
import {test} from 'node:test'
import assert from 'node:assert/strict'
import {detectDurations, formatCountdown, formatDuration} from '../../../vue3/src/fork/timers/detect.ts'

// [step sentence, expected durations as [seconds, maxSeconds?] in order]
const CASES = [
    ['Faire cuire 10 min à feu doux.', [[600]]],
    ['Laisser mijoter 1 h 30 en remuant de temps en temps.', [[5400]]],
    ['Cuire 1h30 au four.', [[5400]]],
    ['Laisser reposer la pâte 1 heure et demie au frais.', [[5400]]],
    ['Faire revenir les oignons 45 s dans le beurre chaud.', [[45]]],
    ['Enfourner pour 20 à 25 minutes, jusqu’à ce que le dessus soit doré.', [[1200, 1500]]],
    ['Blanchir les haricots 2-3 min dans l’eau bouillante salée.', [[120, 180]]],
    ['Préchauffer le four à 180 °C.', []],
    ['Pour 4 personnes.', []],
    ['Mélanger 250 g de farine T55 avec 2 œufs.', []],
    ['Battre 2 œufs en omelette.', []],
    ['Laisser lever 2 heures dans un endroit tiède.', [[7200]]],
    ['Cuire les pâtes 8 minutes, puis égoutter.', [[480]]],
    ['Laisser refroidir une demi-heure avant de démouler.', [[1800]]],
    ['Faire dorer 5 min de chaque côté puis 10 min au four.', [[300], [600]]],
    ['Réserver un quart d’heure au réfrigérateur.', [[900]]],
    ['Laisser mariner entre 2 et 3 heures.', [[7200, 10800]]],
    ['Faire griller 30 secondes à sec.', [[30]]],
    ['Cuire 1 min 30 s au micro-ondes.', [[90]]],
    ['Laisser infuser 5 mn hors du feu.', [[300]]],
    ['Ajouter 3 gousses d’ail et 1 c. à soupe d’huile.', []],
    ['Découper en cubes de 2 cm.', []],
    ['Laisser reposer une nuit (8 h minimum).', [[28800]]],
    ['Cuire 15 s à 45 min selon l’épaisseur.', [[15, 2700]]],
    ['Cuire à couvert 1 h 15 min, puis découvrir.', [[4500]]],
    ['Ajouter 1 h 30 g de sucre.', [[3600]]],
    ['Compter trois quarts d’heure de cuisson.', [[2700]]],
    ['Laisser cuire 6 à 8 h à basse température.', [[21600, 28800]]],
    ['Prolonger la cuisson de vingt-cinq minutes.', [[1500]]],
    ['Laisser reposer dix-huit minutes à couvert.', [[1080]]],
    ['Servir à 20 h, ou réchauffer vers 19 h 30.', []],
    ['Étape 1 - 10 min de préparation.', [[600]]],
    ['Ajouter les herbes 2 et 10 min plus tard.', [[600]]],
    ['Cuire 1 h à 2 h selon la taille.', [[3600, 7200]]],
]

test('at least 20 real French step sentences', () => assert.ok(CASES.length >= 20))

for (const [sentence, expected] of CASES) {
    test(`detects: ${sentence}`, () => {
        const got = detectDurations(sentence).map(d => d.maxSeconds === undefined ? [d.seconds] : [d.seconds, d.maxSeconds])
        assert.deepEqual(got, expected)
    })
}

test('matches keep their exact text', () => {
    const [d] = detectDurations('Enfourner pour 20 à 25 minutes.')
    assert.equal(d.text, '20 à 25 minutes')
    const [h] = detectDurations('Mijoter 1 heure et demie.')
    assert.equal(h.text, '1 heure et demie')
})

test('formatting', () => {
    assert.equal(formatDuration(45), '45 s')
    assert.equal(formatDuration(600), '10 min')
    assert.equal(formatDuration(90), '1 min 30 s')
    assert.equal(formatDuration(5400), '1 h 30')
    assert.equal(formatDuration(7200), '2 h')
    assert.equal(formatCountdown(245000), '4:05')
    assert.equal(formatCountdown(3750000), '1:02:30')
    assert.equal(formatCountdown(-5), '0:00')
})
