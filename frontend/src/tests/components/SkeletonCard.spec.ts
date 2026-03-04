import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SkeletonCard from '../../components/common/SkeletonCard.vue'

describe('SkeletonCard', () => {
  it('renders with default props', () => {
    const wrapper = mount(SkeletonCard)
    const skeletons = wrapper.findAll('.skeleton')
    // 1 title + (3-1) = 2 body lines = 3 total
    expect(skeletons.length).toBe(3)
  })

  it('renders custom number of lines', () => {
    const wrapper = mount(SkeletonCard, { props: { lines: 5 } })
    const skeletons = wrapper.findAll('.skeleton')
    expect(skeletons.length).toBe(5) // 1 title + 4 body
  })

  it('shows action skeleton when showAction is true', () => {
    const wrapper = mount(SkeletonCard, { props: { showAction: true } })
    const actions = wrapper.findAll('.card-actions .skeleton')
    expect(actions.length).toBe(1)
  })

  it('hides action skeleton when showAction is false', () => {
    const wrapper = mount(SkeletonCard, { props: { showAction: false } })
    expect(wrapper.find('.card-actions').exists()).toBe(false)
  })
})
