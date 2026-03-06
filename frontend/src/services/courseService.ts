// Backward compatibility — use spaceService instead
export {
  getSpaces as getCourses,
  createSpace as createCourse,
  getSpace as getCourse,
  deleteSpace as deleteCourse,
  getMembers,
  updateMemberRole,
  removeMember
} from './spaceService'

export { spaceService as courseService } from './spaceService'
