import { CAMPUSES } from '../api/auth'
import type { RegistrationInput } from '../api/auth'

export function validateRegistration(input: RegistrationInput): Partial<Record<keyof RegistrationInput, string>> {
  const errors: Partial<Record<keyof RegistrationInput, string>> = {}
  const nicknameLength = Array.from(input.nickname.trim()).length
  if (nicknameLength < 2 || nicknameLength > 30) errors.nickname = '昵称需为 2～30 个字符。'
  if (!/^[A-Za-z0-9_-]{3,32}$/.test(input.student_no.trim())) errors.student_no = '学号需为 3～32 位字母、数字、下划线或连字符。'
  const passwordLength = Array.from(input.password).length
  if (passwordLength < 8 || passwordLength > 128) errors.password = '密码需为 8～128 个字符。'
  if (!CAMPUSES.some(campus => campus === input.campus)) errors.campus = '请选择所属校区。'
  return errors
}
