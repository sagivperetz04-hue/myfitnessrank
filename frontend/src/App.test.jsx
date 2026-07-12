import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LiftForm } from './App'

function fillForm({ exercise, weight }) {
  fireEvent.change(screen.getByLabelText('Exercise'), { target: { value: exercise } })
  fireEvent.change(screen.getByLabelText('Weight (kg)'), { target: { value: weight } })
}

describe('LiftForm world-record cap', () => {
  it('accepts a weight just under the cap', () => {
    render(<LiftForm username="tester" onResult={vi.fn()} />)
    fillForm({ exercise: 'deadlift', weight: '507' })

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /get my rank/i })).toBeEnabled()
  })

  it('applies the cap per exercise — 400kg bench gets the record message', () => {
    render(<LiftForm username="tester" onResult={vi.fn()} />)
    fillForm({ exercise: 'bench', weight: '400' })

    expect(screen.getByRole('alert')).toHaveTextContent(/really\?/i)
    expect(screen.getByRole('button', { name: /get my rank/i })).toBeDisabled()
  })
})

describe('LiftForm absurd-weight prompts', () => {
  it.each([
    ['600', /are you a car\?/i],
    ['5000', /are you a truck\?/i],
    ['50000', /merkava mk4 barak/i],
    ['200000', /ton 618/i],
  ])('asks the right question for a %skg deadlift', (weight, expected) => {
    render(<LiftForm username="tester" onResult={vi.fn()} />)
    fillForm({ exercise: 'deadlift', weight })

    expect(screen.getByRole('alert')).toHaveTextContent(expected)
    expect(screen.getByRole('button', { name: /get my rank/i })).toBeDisabled()
  })
})
