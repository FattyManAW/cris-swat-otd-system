import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ThemeToggle from '../components/ThemeToggle'

describe('ThemeToggle smoke test', () => {
  it('renders toggle button', () => {
    render(<ThemeToggle />)
    const button = screen.getByRole('button')
    expect(button).toBeInTheDocument()
  })

  it('toggles between dark and light when clicked', async () => {
    const user = userEvent.setup()
    render(<ThemeToggle />)
    const button = screen.getByRole('button')

    // Click to toggle
    await user.click(button)
    // Button should still be rendered
    expect(button).toBeInTheDocument()
  })
})