// src/components/ParameterSliders.tsx
import React, { useState, useEffect, useCallback } from 'react'
import { Parameter } from '../types/parameters'

interface ParameterSlidersProps {
    parameters: Parameter[]
    values: Record<string, number>
    onParameterChange: (name: string, value: number) => void
    onBatchChange?: (changes: Record<string, number>) => void
    isGenerating?: boolean
}

export function ParameterSliders({
    parameters,
    values,
    onParameterChange,
    onBatchChange,
    isGenerating = false
}: ParameterSlidersProps) {
    const [localValues, setLocalValues] = useState<Record<string, number>>(values)
    const [hasChanges, setHasChanges] = useState(false)

    // Mettre à jour les valeurs locales quand les props changent
    useEffect(() => {
        setLocalValues(values)
        setHasChanges(false)
    }, [values])

    // Détection des changements
    useEffect(() => {
        const changed = parameters.some(param =>
            localValues[param.name] !== values[param.name]
        )
        setHasChanges(changed)
    }, [localValues, values, parameters])

    const handleSliderChange = useCallback((name: string, value: number) => {
        setLocalValues(prev => ({ ...prev, [name]: value }))
        onParameterChange(name, value)
    }, [onParameterChange])

    const handleInputChange = useCallback((name: string, value: number) => {
        const param = parameters.find(p => p.name === name)
        if (!param) return

        // Contraindre la valeur aux limites
        const constrainedValue = Math.max(param.min, Math.min(param.max, value))
        setLocalValues(prev => ({ ...prev, [name]: constrainedValue }))
        onParameterChange(name, constrainedValue)
    }, [parameters, onParameterChange])

    const applyAllChanges = useCallback(() => {
        if (onBatchChange && hasChanges) {
            onBatchChange(localValues)
            setHasChanges(false)
        }
    }, [onBatchChange, localValues, hasChanges])

    const resetToDefaults = useCallback(() => {
        const defaults = parameters.reduce((acc, param) => {
            acc[param.name] = param.value
            return acc
        }, {} as Record<string, number>)

        setLocalValues(defaults)
        if (onBatchChange) {
            onBatchChange(defaults)
        } else {
            parameters.forEach(param => {
                onParameterChange(param.name, param.value)
            })
        }
    }, [parameters, onParameterChange, onBatchChange])

    const randomizeValues = useCallback(() => {
        const randomized = parameters.reduce((acc, param) => {
            const range = param.max - param.min
            acc[param.name] = param.min + Math.random() * range
            return acc
        }, {} as Record<string, number>)

        setLocalValues(randomized)
        if (onBatchChange) {
            onBatchChange(randomized)
        } else {
            parameters.forEach(param => {
                onParameterChange(param.name, randomized[param.name])
            })
        }
    }, [parameters, onParameterChange, onBatchChange])

    // Grouper les paramètres par catégorie
    const parametersByCategory = parameters.reduce((acc, param) => {
        const category = param.category || 'Général'
        if (!acc[category]) acc[category] = []
        acc[category].push(param)
        return acc
    }, {} as Record<string, Parameter[]>)

    if (parameters.length === 0) {
        return (
            <div className="parameter-panel">
                <div className="no-parameters">
                    <p>Aucun paramètre ajustable détecté</p>
                    <p style={{ fontSize: '12px', color: '#666' }}>
                        Générez un modèle pour voir les paramètres
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="parameter-panel">
            <div className="parameter-header">
                <h3>Paramètres Ajustables</h3>
                <div className="parameter-controls">
                    {onBatchChange && hasChanges && (
                        <button
                            className="button small primary"
                            onClick={applyAllChanges}
                            disabled={isGenerating}
                        >
                            Appliquer
                        </button>
                    )}
                    <button
                        className="button small"
                        onClick={resetToDefaults}
                        disabled={isGenerating}
                        title="Remettre aux valeurs par défaut"
                    >
                        Reset
                    </button>
                    <button
                        className="button small"
                        onClick={randomizeValues}
                        disabled={isGenerating}
                        title="Valeurs aléatoires"
                    >
                        🎲
                    </button>
                </div>
            </div>

            <div className="parameter-categories">
                {Object.entries(parametersByCategory).map(([category, categoryParams]) => (
                    <ParameterCategory
                        key={category}
                        category={category}
                        parameters={categoryParams}
                        values={localValues}
                        onSliderChange={handleSliderChange}
                        onInputChange={handleInputChange}
                        disabled={isGenerating}
                    />
                ))}
            </div>

            {hasChanges && (
                <div className="parameter-status">
                    <small>⚠️ Modifications non appliquées</small>
                </div>
            )}
        </div>
    )
}

interface ParameterCategoryProps {
    category: string
    parameters: Parameter[]
    values: Record<string, number>
    onSliderChange: (name: string, value: number) => void
    onInputChange: (name: string, value: number) => void
    disabled: boolean
}

function ParameterCategory({
    category,
    parameters,
    values,
    onSliderChange,
    onInputChange,
    disabled
}: ParameterCategoryProps) {
    const [isCollapsed, setIsCollapsed] = useState(false)

    return (
        <div className="parameter-category">
            <div
                className="category-header"
                onClick={() => setIsCollapsed(!isCollapsed)}
            >
                <span>{category}</span>
                <span className="collapse-icon">{isCollapsed ? '▶' : '▼'}</span>
            </div>

            {!isCollapsed && (
                <div className="category-parameters">
                    {parameters.map((param) => (
                        <ParameterRow
                            key={param.name}
                            parameter={param}
                            value={values[param.name] ?? param.value}
                            onSliderChange={onSliderChange}
                            onInputChange={onInputChange}
                            disabled={disabled}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}

interface ParameterRowProps {
    parameter: Parameter
    value: number
    onSliderChange: (name: string, value: number) => void
    onInputChange: (name: string, value: number) => void
    disabled: boolean
}

function ParameterRow({
    parameter,
    value,
    onSliderChange,
    onInputChange,
    disabled
}: ParameterRowProps) {
    const [inputValue, setInputValue] = useState(value.toString())

    useEffect(() => {
        setInputValue(value.toString())
    }, [value])

    const handleInputBlur = () => {
        const numValue = parseFloat(inputValue)
        if (!isNaN(numValue)) {
            onInputChange(parameter.name, numValue)
        } else {
            setInputValue(value.toString())
        }
    }

    const handleInputKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleInputBlur()
        }
    }

    const formatValue = (val: number): string => {
        return val % 1 === 0 ? val.toString() : val.toFixed(1)
    }

    return (
        <div className="parameter-row">
            <div className="parameter-info">
                <label className="parameter-label">
                    {parameter.description || parameter.name}
                    {parameter.unit && <span className="parameter-unit"> ({parameter.unit})</span>}
                </label>
                <div className="parameter-range">
                    <small>{formatValue(parameter.min)} - {formatValue(parameter.max)}</small>
                </div>
            </div>

            <div className="parameter-controls-row">
                <input
                    type="range"
                    className="parameter-slider"
                    min={parameter.min}
                    max={parameter.max}
                    step={parameter.step}
                    value={value}
                    onChange={(e) => onSliderChange(parameter.name, parseFloat(e.target.value))}
                    disabled={disabled}
                />

                <input
                    type="number"
                    className="parameter-input"
                    min={parameter.min}
                    max={parameter.max}
                    step={parameter.step}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onBlur={handleInputBlur}
                    onKeyDown={handleInputKeyDown}
                    disabled={disabled}
                />
            </div>

            <div className="parameter-value-display">
                <span className="current-value">
                    {formatValue(value)}{parameter.unit}
                </span>
            </div>
        </div>
    )
}