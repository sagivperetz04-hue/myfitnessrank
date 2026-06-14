import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LiftForm } from './App'

function fillForm({ exercise, weight }) {
  fireEvent.change(screen.getByLabelText('Exercise'), { target: { value: exercise } })
  fireEvent.change(screen.getByLabelText('Weight (kg)'), { target: { value: weight } })
}

describe('LiftForm world-record cap', () => {
  it('shows the over-limit message and blocks submit for a 600kg deadlift', () => {
    render(<LiftForm username="tester" onResult={vi.fn()} />)
    fillForm({ exercise: 'deadlift', weight: '600' })

    expect(screen.getByRole('alert')).toHaveTextContent(/really\?/i)
    expect(screen.getByRole('button', { name: /get my rank/i })).toBeDisabled()
  })

  it('accepts a weight just under the cap', () => {
    render(<LiftForm username="tester" onResult={vi.fn()} />)
    fillForm({ exercise: 'deadlift', weight: '507' })

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /get my rank/i })).toBeEnabled()
  })

  it('applies the cap per exercise — 400kg bench is rejected', () => {
    render(<LiftForm username="tester" onResult={vi.fn()} />)
    fillForm({ exercise: 'bench', weight: '400' })

    expect(screen.getByRole('alert')).toBeInTheDocument()
  })
})
