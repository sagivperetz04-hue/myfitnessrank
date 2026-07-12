import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LiftForm } from './App'

function fillForm({ exercise, weight, bodyweight }) {
  fireEvent.change(screen.getByLabelText('Exercise'), { target: { value: exercise } })
  fireEvent.change(screen.getByLabelText('Weight (kg)'), { target: { value: weight } })
  if (bodyweight !== undefined) {
    fireEvent.change(screen.getByLabelText('Bodyweight (kg)'), { target: { value: bodyweight } })
  }
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

describe('LiftForm bodyweight cap', () => {
  it('accepts a bodyweight at the cap', () => {
    render(<LiftForm username="tester" onResult={vi.fn()} />)
    fillForm({ exercise: 'deadlift', weight: '100', bodyweight: '640' })

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /get my rank/i })).toBeEnabled()
  })

  it.each([
    ['700', /are you a car\?/i],
    ['5000', /are you a truck\?/i],
    ['50000', /merkava mk4 barak/i],
    ['9239123', /ton 618/i],
  ])('blocks and asks the right question for a %skg bodyweight', (bodyweight, expected) => {
    render(<LiftForm username="tester" onResult={vi.fn()} />)
    fillForm({ exercise: 'deadlift', weight: '100', bodyweight })

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent(expected)
    expect(alert).toHaveTextContent(/capped at 640 kg/i)
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
